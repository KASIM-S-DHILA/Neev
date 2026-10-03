export const formats =
  ".pdf,.txt,.md,.ppt,.pptx,.mp4,.mkv,.mov,.webm,.mp3,.wav,.m4a,.ogg,.flac,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp";
export const maxBytes = 2 * 1024 ** 3;
export function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 ** 2) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 ** 3) return `${(size / 1024 ** 2).toFixed(1)} MB`;
  return `${(size / 1024 ** 3).toFixed(1)} GB`;
}
