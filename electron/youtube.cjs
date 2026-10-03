function youtubePlaybackUrl(value) {
  if (typeof value !== 'string' || value.length > 200) throw new Error('Invalid YouTube playback link.');
  const url = new URL(value);
  const video = url.searchParams.get('v');
  const time = url.searchParams.get('t');
  if (url.protocol !== 'https:' || url.hostname !== 'www.youtube.com' || url.port || url.username || url.password ||
      url.pathname !== '/watch' || url.hash || !/^[A-Za-z0-9_-]{11}$/.test(video || '') ||
      [...url.searchParams.keys()].some(key=> !['v','t'].includes(key)) || url.searchParams.getAll('v').length !== 1 ||
      url.searchParams.getAll('t').length > 1 || (time !== null && (!/^\d+$/.test(time) || Number(time)>14400)))
    throw new Error('Invalid YouTube playback link.');
  return 'https://www.youtube.com/watch?v=' + video + (time === null ? '' : '&t=' + Number(time));
}
module.exports = {youtubePlaybackUrl};
