const KEY = "ceekr_sidebar_collapsed";

export function loadSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(KEY) === "true";
  } catch {
    return false;
  }
}

export function saveSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(KEY, String(collapsed));
  } catch {
    // localStorage unavailable
  }
}
