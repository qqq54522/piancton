import type { Tag, TagWithCount } from '@client/src/types/api';

export interface TagTreeNode extends TagWithCount {
  children: TagTreeNode[];
  depth: number;
}

export function buildTagTree(tags: TagWithCount[]): TagTreeNode[] {
  const map = new Map<string, TagTreeNode>();
  const roots: TagTreeNode[] = [];

  for (const tag of tags) {
    map.set(tag.id, { ...tag, children: [], depth: 0 });
  }

  for (const tag of tags) {
    const node = map.get(tag.id)!;
    if (tag.parentId && map.has(tag.parentId)) {
      const parent = map.get(tag.parentId)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  const updateDepth = (nodes: TagTreeNode[], depth: number) => {
    for (const node of nodes) {
      node.depth = depth;
      updateDepth(node.children, depth + 1);
    }
  };
  updateDepth(roots, 0);

  return roots;
}

export function flattenTree(nodes: TagTreeNode[]): TagTreeNode[] {
  const result: TagTreeNode[] = [];
  const walk = (list: TagTreeNode[]) => {
    for (const node of list) {
      result.push(node);
      walk(node.children);
    }
  };
  walk(nodes);
  return result;
}

export function getAncestorIds(tagId: string, tags: Tag[]): string[] {
  const ancestors: string[] = [];
  let current = tags.find((t) => t.id === tagId);
  while (current?.parentId) {
    ancestors.push(current.parentId);
    current = tags.find((t) => t.id === current!.parentId);
  }
  return ancestors;
}

export function getDescendantIds(tagId: string, tags: Tag[]): string[] {
  const descendants: string[] = [];
  const collect = (id: string) => {
    for (const child of tags) {
      if (child.parentId === id) {
        descendants.push(child.id);
        collect(child.id);
      }
    }
  };
  collect(tagId);
  return descendants;
}
