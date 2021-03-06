
from datetime import datetime
from .helpers import parseDateTime
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

PROP_KEY_SLUG = "snapshot_slug"
PROP_KEY_DATE = "snapshot_date"
PROP_KEY_NAME = "snapshot_name"
PROP_TYPE = "type"
PROP_VERSION = "version"
PROP_PROTECTED = "protected"
PROP_RETAINED = "retained"


class AbstractSnapshot(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def slug(self) -> str:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    @abstractmethod
    def date(self) -> datetime:
        pass


class DriveSnapshot(AbstractSnapshot):
    """
    Represents a Hass.io snapshot stored on Google Drive
    """
    def __init__(self, source: Dict[Any, Any]):
        self.source = source.copy()
        self._date = parseDateTime(self.source.get('appProperties')[PROP_KEY_DATE])

    def id(self) -> str:
        return str(self.source.get('id'))

    def name(self) -> str:
        return self.source.get('appProperties')[PROP_KEY_NAME]  # type: ignore

    def slug(self) -> str:
        return self.source.get('appProperties')[PROP_KEY_SLUG]  # type: ignore

    def size(self) -> int:
        return self.source.get('size')  # type: ignore

    def date(self) -> datetime:
        return self._date

    def snapshotType(self) -> str:
        props = self.source.get('appProperties')
        if PROP_TYPE in props:
            return props[PROP_TYPE]
        return "full"

    def version(self) -> str:
        props = self.source.get('appProperties')
        if PROP_VERSION in props:
            return props[PROP_VERSION]
        return "?"

    def protected(self) -> bool:
        props = self.source.get('appProperties')
        if PROP_PROTECTED in props:
            return props[PROP_PROTECTED] == "true" or props[PROP_PROTECTED] == "True"
        return False

    def retained(self) -> bool:
        props = self.source.get('appProperties')
        if PROP_RETAINED in props:
            return props[PROP_RETAINED] == "true" or props[PROP_RETAINED] == "True"
        return False

    def setRetain(self, retain):
        self.source.get('appProperties')[PROP_RETAINED] = str(retain)

    def __str__(self) -> str:
        return "<Drive: {0} Name: {1} Id: {2}>".format(self.slug(), self.name(), self.id())

    def __format__(self, format_spec: str) -> str:
        return self.__str__()

    def __repr__(self) -> str:
        return self.__str__()


class HASnapshot(AbstractSnapshot):
    """
    Represents a Hass.io snapshot stored locally in Home Assistant
    """
    def __init__(self, source: Dict[str, Any], retained=False):
        self.source: Dict[str, Any] = source.copy()
        self._retained = retained
        self._date = parseDateTime(self.source['date'])

    def name(self) -> str:
        return str(self.source['name'])

    def slug(self) -> str:
        return str(self.source['slug'])

    def size(self) -> int:
        return int(self.source['size']) * 1024 * 1024

    def date(self) -> datetime:
        return self._date

    def snapshotType(self) -> str:
        return str(self.source['type'])

    def version(self) -> str:
        return str(self.source['homeassistant'])

    def protected(self) -> bool:
        return bool(self.source['protected'])

    def retained(self) -> bool:
        return self._retained

    def __str__(self) -> str:
        return "<HA: {0} Name: {1} {2}>".format(self.slug(), self.name(), self.date().isoformat())

    def __format__(self, format_spec: str) -> str:
        return self.__str__()

    def __repr__(self) -> str:
        return self.__str__()


class Snapshot(object):
    """
    Represents a Hass.io snapshot stored on Google Drive, locally in
    Home Assistant, or a pending snapshot we expect to see show up later
    """
    def __init__(self, snapshot: Optional[AbstractSnapshot]):
        self.driveitem: Optional[DriveSnapshot] = None
        self.pending: bool = False
        self.ha: Optional[HASnapshot] = None
        self.donwloading = -1
        self.donwload_failed = False
        if isinstance(snapshot, HASnapshot):
            self.ha = snapshot
            self.driveitem = None
            self.pending = False
        elif isinstance(snapshot, DriveSnapshot):
            self.driveitem = snapshot
            self.ha = None
            self.pending = False
        else:
            self.pending = True
        self.pending_name: Optional[str] = ""
        self.pending_date: Optional[datetime] = None
        self.pending_slug: Optional[str] = None
        self.uploading_pct: int = -1
        self.pendingHasFailed: bool = False
        self.will_backup: bool = True
        self.restoring = None
        self._deleteNextFromDrive = None
        self._deleteNextFromHa = None
        self._pending_retain_drive = False
        self._pending_retain_ha = False

    @property
    def deleteNextFromDrive(self):
        return self._deleteNextFromDrive

    @deleteNextFromDrive.setter
    def deleteNextFromDrive(self, delete):
        self._deleteNextFromDrive = delete

    @property
    def deleteNextFromHa(self):
        return self._deleteNextFromHa

    @deleteNextFromHa.setter
    def deleteNextFromHa(self, delete):
        self._deleteNextFromHa = delete

    def setPending(self, name: str, date: datetime, retain_drive: bool, retain_ha: bool) -> None:
        self.pending_name = name
        self.pending_date = date
        self.pending_slug = "PENDING"
        self.pending = True
        self._pending_retain_drive = retain_drive
        self._pending_retain_ha = retain_ha

    def endPending(self, slug: str) -> None:
        self.pending_slug = slug

    def pendingFailed(self) -> None:
        self.pendingHasFailed = True

    def setWillBackup(self, will: bool) -> None:
        self.will_backup = will

    def name(self) -> str:
        if self.driveitem:
            return self.driveitem.name()
        elif self.ha:
            return self.ha.name()
        elif self.pending and self.pending_name:
            return self.pending_name
        else:
            return "error"

    def slug(self) -> str:
        if self.driveitem:
            return self.driveitem.slug()
        elif self.ha:
            return self.ha.slug()
        elif self.pending and self.pending_slug:
            return self.pending_slug
        else:
            return "error"

    def size(self) -> int:
        if self.driveitem:
            return self.driveitem.size()
        elif self.ha:
            return self.ha.size()
        else:
            return 0

    def snapshotType(self) -> str:
        if self.ha:
            return self.ha.snapshotType()
        elif self.driveitem:
            return self.driveItem.snapshotType()
        else:
            return "pending"

    def version(self) -> str:
        if self.ha:
            return self.ha.snapshotType()
        elif self.driveitem:
            return self.driveitem.snapshotType()
        else:
            return "?"

    def protected(self) -> bool:
        if self.ha:
            return self.ha.protected()
        elif self.driveitem:
            return self.driveitem.protected()
        else:
            return False

    def date(self) -> datetime:
        if self.driveitem:
            return self.driveitem.date()
        elif self.ha:
            return self.ha.date()
        elif self.pending and self.pending_date:
            return self.pending_date
        else:
            return datetime.now()

    def sizeString(self) -> str:
        size_bytes = float(self.size())
        if size_bytes <= 1024.0:
            return str(int(size_bytes)) + " B"
        if size_bytes <= 1024.0 * 1024.0:
            return str(int(size_bytes / 1024.0)) + " kB"
        if size_bytes <= 1024.0 * 1024.0 * 1024.0:
            return str(int(size_bytes / (1024.0 * 1024.0))) + " MB"
        return str(int(size_bytes / (1024.0 * 1024.0 * 1024.0))) + " GB"

    def setDownloading(self, percent):
        self.donwloading = percent
        self.downloadFailed = False

    def downloadFailed(self):
        self.donwload_failed = True

    def status(self) -> str:
        if self.isRestoring():
            if self.restoring:
                return "Restoring"
            else:
                return "Restore Complete"
        if self.isDownloading():
            if self.donwload_failed:
                return "Loading Failed!"
            if self.donwloading == 100:
                return "Refreshing snapshot".format(self.donwloading)
            return "Loading {0}%".format(self.donwloading)
        if self.isInDrive() and self.isInHA():
            return "Backed Up"
        if self.isInDrive() and not self.isInHA():
            return "Drive Only"
        if not self.isInDrive() and self.isInHA() and self.uploading_pct >= 0:
            return "Uploading {}%".format(self.uploading_pct)
        if not self.isInDrive() and self.isInHA():
            if self.will_backup:
                return "Waiting"
            else:
                return "Hass.io Only"
        if self.pending:
            return "Pending"
        return "Invalid State"

    def isDownloading(self):
        return self.donwloading >= 0

    def isRestoring(self):
        return self.restoring is not None

    def setDrive(self, drive: DriveSnapshot) -> None:
        self.driveitem = drive
        self.pending_name = None
        self.pending_date = None
        self.pending_slug = None
        self.uploading_pct = -1
        self.pending = False

    def setHA(self, ha: HASnapshot) -> None:
        self.ha = ha
        self.pending_name = None
        self.pending_date = None
        self.pending_slug = None
        self.uploading_pct = -1
        self.pending = False
        self.donwloading = -1
        self.donwload_failed = False

    def isInDrive(self) -> bool:
        return self.driveitem is not None

    def isInHA(self) -> bool:
        return self.ha is not None

    def isPending(self) -> bool:
        return self.pending and not self.isInHA() and not self.pendingHasFailed

    def isDeleted(self) -> bool:
        return not self.isPending() and not self.isInHA() and not self.isInDrive()

    def update(self, snapshot: AbstractSnapshot) -> None:
        if isinstance(snapshot, HASnapshot):
            self.ha = snapshot
        else:
            self.drive = snapshot

    def details(self):
        if self.isInHA():
            return self.ha.source
        elif self.isInDrive():
            return self.drive.details()
        else:
            return {}

    def uploading(self, percent: int) -> None:
        self.uploading_pct = percent

    def driveRetained(self):
        return self.isInDrive() and (self.driveitem.retained() or self._pending_retain_drive)

    def haRetained(self):
        return self.isInHA() and (self.ha.retained() or self._pending_retain_ha)

    def __str__(self) -> str:
        return "<Slug: {0} Ha: {1} Drive: {2} Pending: {3} {4}>".format(self.slug(), self.ha, self.driveitem, self.pending, self.date().isoformat())

    def __format__(self, format_spec: str) -> str:
        return self.__str__()

    def __repr__(self) -> str:
        return self.__str__()
