from rest_framework.renderers import BaseRenderer


class ServerSentEventRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        return str(data).encode("utf-8")
