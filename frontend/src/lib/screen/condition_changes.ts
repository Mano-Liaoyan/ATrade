// The change marks of the condition card of the AI assistant (docs/architecture/assistant.md 25.12.4). The card
// compares the groups of the screen with the groups of the definition before: the screen before update_screen, or
// the source screen of create_screen.
// - A tag with the same 3 parts is the same condition.
// - A tag with the same subject and operation and another value is a changed value. The start instruments and the
//   order have one tag each, so another tag there is a changed value too.
// - Each other new tag is added. Each other old tag is removed and stays after the tag that was before it.
import type { ConditionGroup, ConditionTag } from './condition_bar';

export type ConditionChange = 'same' | 'added' | 'removed' | 'changed';

export interface MarkedConditionTag extends ConditionTag {
  change: ConditionChange;
  /** The old tag of a changed value. Else null. */
  previous: ConditionTag | null;
}

export interface MarkedConditionGroup extends Omit<ConditionGroup, 'tags'> {
  tags: MarkedConditionTag[];
}

interface Entry {
  tag: MarkedConditionTag;
  oldIndex: number | null;
}

function isSame(first: ConditionTag, second: ConditionTag): boolean {
  return first.subject === second.subject && first.operation === second.operation && first.value === second.value;
}

function isSameCondition(first: ConditionTag, second: ConditionTag): boolean {
  return first.subject === second.subject && first.operation === second.operation;
}

function findUnused(oldTags: ConditionTag[], used: Set<number>, matches: (tag: ConditionTag) => boolean): number | null {
  const index = oldTags.findIndex((tag, tagIndex) => !used.has(tagIndex) && matches(tag));
  return index < 0 ? null : index;
}

function insertRemoved(entries: Entry[], oldTags: ConditionTag[], used: Set<number>): Entry[] {
  const result = [...entries];
  oldTags.forEach((tag, oldIndex) => {
    if (used.has(oldIndex)) {
      return;
    }
    const before = result.findLastIndex((entry) => entry.oldIndex !== null && entry.oldIndex < oldIndex);
    result.splice(before + 1, 0, { tag: { ...tag, change: 'removed', previous: null }, oldIndex });
  });
  return result;
}

function markTags(oldTags: ConditionTag[], newTags: ConditionTag[], isSingle: boolean): MarkedConditionTag[] {
  const used = new Set<number>();
  const sameIndexes = newTags.map((tag) => {
    const index = findUnused(oldTags, used, (oldTag) => isSame(oldTag, tag));
    if (index !== null) {
      used.add(index);
    }
    return index;
  });
  const entries = newTags.map((tag, newIndex): Entry => {
    const sameIndex = sameIndexes[newIndex] ?? null;
    if (sameIndex !== null) {
      return { tag: { ...tag, change: 'same', previous: null }, oldIndex: sameIndex };
    }
    const changedIndex = findUnused(oldTags, used, (oldTag) => isSingle || isSameCondition(oldTag, tag));
    if (changedIndex === null) {
      return { tag: { ...tag, change: 'added', previous: null }, oldIndex: null };
    }
    used.add(changedIndex);
    return { tag: { ...tag, change: 'changed', previous: oldTags[changedIndex] ?? null }, oldIndex: changedIndex };
  });
  return insertRemoved(entries, oldTags, used).map((entry) => entry.tag);
}

/** The groups of the screen with the change of each tag. Without `previous`, each tag is the same. */
export function markConditionChanges(previous: ConditionGroup[] | null, current: ConditionGroup[]): MarkedConditionGroup[] {
  return current.map((group, index) => {
    const oldTags = previous === null ? group.tags : (previous[index]?.tags ?? []);
    // The start instruments and the order are the first and the last group, with one tag each.
    const isSingle = index === 0 || index === current.length - 1;
    return { ...group, tags: markTags(oldTags, group.tags, isSingle) };
  });
}
