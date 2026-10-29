export type PageId = "home" | "assistant" | "about";

export function pageFromPath(pathname: string): PageId {
  if (pathname === "/assistant") return "assistant";
  if (pathname === "/about") return "about";
  return "home";
}

export function pathForPage(page: PageId): string {
  if (page === "assistant") return "/assistant";
  if (page === "about") return "/about";
  return "/";
}
