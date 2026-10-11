import * as vscode from 'vscode';
import { Connection } from '../connection/connect';
import { Profiles } from '../state/profiles';
export interface Navigation {label:string;command:string;description?:string;icon?:string;args?:unknown[]}
export class NavigationTree implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly events=new vscode.EventEmitter<void>();readonly onDidChangeTreeData=this.events.event;
  constructor(private readonly items:()=>Navigation[]){}
  refresh():void{this.events.fire();}
  getTreeItem(item:vscode.TreeItem):vscode.TreeItem{return item;}
  getChildren():vscode.TreeItem[]{return this.items().map(entry=>{
    const item=new vscode.TreeItem(entry.label);item.description=entry.description;item.tooltip=entry.description||entry.label;
    item.iconPath=new vscode.ThemeIcon(entry.icon||'circle-outline');item.command={command:entry.command,title:entry.label,arguments:entry.args||[]};
    item.accessibilityInformation={label:[entry.label,entry.description].filter(Boolean).join(', ')};return item;
  });}
}
export function connectionTree(connection:Connection,profiles:Profiles):NavigationTree {
  return new NavigationTree(()=>[
    ...profiles.list().map(profile=>({label:profile.label,description:connection.profile?.id===profile.id?'Connected':`${profile.harness} · ${profile.transport}`,command:'netclaw.selectConnection',args:[profile.id],icon:'remote'})),
    {label:'Add an existing installation',command:'netclaw.addConnection',icon:'add'},
  ]);
}
