"""One bounded network helper per submitted YouTube link; no cookies/proxies."""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .youtube import REVISION, parse_url, validate_snapshot
from .job_errors import ExtractionFailure

ISSUES = {
    "TranscriptsDisabled": "Captions are disabled for this video. The link is saved; add a transcript or permitted media copy.",
    "NoTranscriptFound": "No captions in the requested language. Choose an available language and import again.",
    "RequestBlocked": "YouTube blocked caption access. The link is saved. Try again later or add a transcript/media copy.",
    "IpBlocked": "YouTube blocked caption access. The link is saved. Try again later or add a transcript/media copy.",
    "VideoUnavailable": "This video is unavailable. The link is saved; check access on YouTube.",
    "VideoUnplayable": "This video cannot be accessed by the caption reader. The link is saved.",
    "AgeRestricted": "This video requires authentication. The link is saved; authenticated caption fetching is unavailable.",
}


def fetch(request):
    from requests import Session
    from youtube_transcript_api import YouTubeTranscriptApi
    video_id, url = parse_url(request["url"])
    if request["video_id"] != video_id:
        raise ValueError("Source identity mismatch")
    snapshot = {"revision": REVISION, "url": url, "video_id": video_id, "requested_language": request["language"],
        "language_code": None, "is_generated": None, "tracks": [], "snippets": [], "issue": None}
    class BoundedSession(Session):
        def request(self, method, url, **kwargs):
            kwargs["timeout"] = (5, 10)
            return super().request(method, url, **kwargs)
        def send(self, request, **kwargs):
            parsed = urlsplit(request.url)
            if parsed.scheme != "https" or parsed.hostname not in ("www.youtube.com", "youtube.com", "consent.youtube.com", "consent.google.com") or parsed.port is not None or parsed.username:
                raise ValueError("Unexpected caption endpoint")
            kwargs["stream"] = True
            response = super().send(request, **kwargs)
            chunks, size = [], 0
            try:
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 8 * 1024**2:
                        raise ValueError("Caption response exceeds 8 MB")
                    chunks.append(chunk)
                response._content = b"".join(chunks)
                response._content_consumed = True
                return response
            finally:
                response.close()
    with BoundedSession() as session:
        session.trust_env = False
        try:
            tracks = list(YouTubeTranscriptApi(http_client=session).list(video_id))
            snapshot["tracks"] = [{"language": track.language, "language_code": track.language_code, "is_generated": track.is_generated} for track in tracks]
            matching = [track for track in tracks if track.language_code == request["language"]]
            if not matching:
                snapshot["issue"] = ISSUES["NoTranscriptFound"]
            else:
                selected = min(matching, key=lambda track: track.is_generated)
                fetched = selected.fetch()
                if fetched.video_id != video_id or fetched.language_code != selected.language_code or fetched.is_generated != selected.is_generated:
                    raise ValueError("Fetched caption provenance mismatch")
                snapshot.update(language_code=fetched.language_code, is_generated=fetched.is_generated,
                    snippets=fetched.to_raw_data())
                if not snapshot["snippets"]:
                    snapshot["issue"] = "The caption track is empty. The link is saved."
        except Exception as error:
            snapshot.update(snippets=[], language_code=None, is_generated=None)
            snapshot["issue"] = ISSUES.get(type(error).__name__, "Caption fetching failed or timed out. The link is saved; try again later or add a transcript/media copy.")
    try:
        return validate_snapshot(snapshot)
    except (ExtractionFailure, ValueError, TypeError):
        snapshot.update(tracks=[], snippets=[], language_code=None, is_generated=None,
            issue="Caption data was invalid or exceeded the processing limits. The link is saved.")
        return validate_snapshot(snapshot)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(fetch(request), ensure_ascii=False, separators=(",", ":"), allow_nan=False))
