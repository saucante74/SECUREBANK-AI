export type PageId = "home" | "assistant";

export function pageFromPath(pathname: string): PageId {
  return pathname === "/assistant" ? "assistant" : "home";
}

export function pathForPage(page: PageId): string {
  return page === "assistant" ? "/assistant" : "/";
}
