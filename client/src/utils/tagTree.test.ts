import { describe, expect, it } from 'vitest';

import type { TagWithCount } from '@client/src/types/api';
import { buildTagTree, getAncestorIds, getDescendantIds } from './tagTree';


const tags: TagWithCount[] = [
  { id: 'a', name: 'A', color: '#000', parentId: null, isSecondary: false, nodeType: 'custom', assignable: true, status: 'active', sortOrder: 0, imageCount: 0 },
  { id: 'b', name: 'B', color: '#000', parentId: 'a', isSecondary: false, nodeType: 'custom', assignable: true, status: 'active', sortOrder: 1, imageCount: 0 },
  { id: 'c', name: 'C', color: '#000', parentId: 'b', isSecondary: false, nodeType: 'custom', assignable: true, status: 'active', sortOrder: 2, imageCount: 0 },
];

describe('tag tree', () => {
  it('builds hierarchy and calculates relatives', () => {
    const tree = buildTagTree(tags);
    expect(tree[0].children[0].children[0].id).toBe('c');
    expect(getAncestorIds('c', tags)).toEqual(['b', 'a']);
    expect(getDescendantIds('a', tags)).toEqual(['b', 'c']);
  });
});
