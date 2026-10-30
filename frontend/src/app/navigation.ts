export type PageId = "home" | "assistant" | "evaluation" | "about";

export function pageFromPath(pathname: string): PageId {
  if (pathname === "/assistant") return "assistant";
  if (pathname === "/evaluation") return "evaluation";
  if (pathname === "/about") return "about";
  return "home";
}

export function pathForPage(page: PageId): string {
  if (page === "assistant") return "/assistant";
  if (page === "evaluation") return "/evaluation";
  if (page === "about") return "/about";
  return "/";
}
