import type { DragEvent } from 'react';
import type { Node } from './model';
interface Props { node: Node; path: readonly number[]; selected: string; onSelect: (path: readonly number[]) => void; onDropItem: (path: readonly number[], item: string) => void }
/** Render one selectable typed tree node. @param props Node and event callbacks. @returns Accessible tree branch. */
export function TreeView(props: Props) {
  const key = props.path.join('.');
  /** Select this slot for keyboard insertion. @returns Nothing. */
  function select() { props.onSelect(props.path); }
  /** Allow dropping on this slot. @param event Drag event. @returns Nothing. */
  function allowDrop(event: DragEvent) { event.preventDefault(); event.stopPropagation(); }
  /** Apply a dragged palette item. @param event Drop event. @returns Nothing. */
  function drop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    props.onDropItem(props.path,event.dataTransfer.getData('text/plain'));
  }
  /** Render a child with its stable path. @param child Child node. @param index Child position. @returns Nested branch. */
  function childView(child: Node, index: number) {
    return <TreeView key={index} node={child} path={[...props.path,index]} selected={props.selected} onSelect={props.onSelect} onDropItem={props.onDropItem}/>;
  }
  const label = props.node.op === 'hole' ? `Empty ${props.node.kind} slot` : props.node.name ?? props.node.op;
  return <div className="tree-branch">
    <button type="button" className={`tree-node ${props.node.op === 'hole' ? 'empty' : ''} ${key === props.selected ? 'selected' : ''}`} onClick={select} onDragOver={allowDrop} onDrop={drop} aria-pressed={key === props.selected}>
    <span>{label}</span><small>{props.node.kind}</small></button>{props.node.children.length > 0 && <div className="tree-children">{props.node.children.map(childView)}</div>}</div>;
}
