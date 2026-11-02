
class DriveItem:
    def __init__(self, item:dict):
        self.item = item

    @property
    def name(self) -> str:
        return self.item.get("name", "")

    @property
    def id(self)->str:
        return self.item.get("id","")

    @property
    def createdDateTime(self) -> str:
        return self.item.get("createdDateTime", "")

    @property
    def size(self) -> str:
        return self.item.get("size", "")

    @property
    def is_file(self)->bool:
        return "file" in self.item

    @property
    def is_folder(self)->bool:
        return "folder" in self.item

    @property
    def is_deleted(self) -> str:
        return "deleted" in self.item

    @property
    def parentId(self) -> str:
        parentReference = self.item.get("parentReference", {})
        if parentReference:
            return parentReference.get("id","")
        else:
            print(f'no parentReference found')
            return ''

    def __str__(self):
        text=''
        for key, value in self.item.items():
            text += f"{key}: {value}\n"

        return text