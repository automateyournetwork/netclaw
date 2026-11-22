import * as vscode from "vscode";
export interface Navigation {
  label: string;
  command: string;
  description?: string;
  icon?: string;
  args?: unknown[];
  /** VS Code `viewItem` context value; connection rows use `netclaw.connection` for Rename/Remove menus. */
  contextValue?: string;
  /** Saved connection profile id, passed to row-level commands. */
  profileId?: string;
}
export class NavigationTree
  implements vscode.TreeDataProvider<vscode.TreeItem>, vscode.Disposable
{
  private events = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.events.event;
  constructor(private items: () => Navigation[]) {}
  refresh() {
    this.events.fire();
  }
  getTreeItem(item: vscode.TreeItem) {
    return item;
  }
  getChildren() {
    return this.items().map((entry) => {
      const item = new vscode.TreeItem(entry.label);
      item.description = entry.description;
      item.tooltip = entry.description || entry.label;
      item.iconPath = new vscode.ThemeIcon(entry.icon || "circle-outline");
      if (entry.contextValue) item.contextValue = entry.contextValue;
      if (entry.profileId) (item as vscode.TreeItem & { profileId?: string }).profileId = entry.profileId;
      item.command = {
        command: entry.command,
        title: entry.label,
        arguments: entry.args || [],
      };
      return item;
    });
  }
  dispose() {
    this.events.dispose();
  }
}
