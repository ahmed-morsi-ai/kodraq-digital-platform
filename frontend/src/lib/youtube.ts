const YOUTUBE_HOSTS = [
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
];

export function getEmbedUrl(url: string): string | null {
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url.trim());
  } catch {
    return null;
  }

  if (parsedUrl.protocol !== "https:" && parsedUrl.protocol !== "http:") {
    return null;
  }

  const hostname = parsedUrl.hostname.toLowerCase();
  let videoId: string | null = null;

  if (hostname === "youtu.be") {
    videoId = parsedUrl.pathname.split("/").filter(Boolean)[0] ?? null;
  } else if (YOUTUBE_HOSTS.includes(hostname)) {
    if (parsedUrl.pathname === "/watch") {
      videoId = parsedUrl.searchParams.get("v");
    } else {
      videoId = parsedUrl.pathname.match(/^\/embed\/([^/]+)\/?$/)?.[1] ?? null;
    }
  }

  if (!videoId || !/^[\w-]{11}$/.test(videoId)) return null;
  return `https://www.youtube.com/embed/${videoId}`;
}