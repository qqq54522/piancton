from fastapi.responses import FileResponse


class StorageFileResponse(FileResponse):
    """Release remote temporary files even when sending fails or the client disconnects."""

    def __init__(self, path, *, release, **kwargs):
        super().__init__(path, **kwargs)
        self.release_file = release

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.release_file(self.path)
