const PIXELS_PER_LINE = 16;
const WHEEL_OWNER_SELECTOR = [
  '[data-scroll-owner]',
  '[data-slot="scroll-area-viewport"]',
  '.terminal-scroll-owned',
  '.terminal-workspace-scroll-owned',
].join(', ');

type WheelDelta = {
  deltaX: number;
  deltaY: number;
};

type ScrollAxis = 'x' | 'y';

export function attachTerminalWheelScrollOwnership(root: HTMLElement) {
  function handleWheel(event: WheelEvent) {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey) {
      return;
    }

    const target = event.target instanceof Element ? event.target : null;
    if (!target || !root.contains(target)) {
      return;
    }

    const wheelDelta = normalizeWheelDelta(event, root);
    if (wheelDelta.deltaX === 0 && wheelDelta.deltaY === 0) {
      return;
    }

    const scrollOwners = getScrollableWheelOwners(target, root);
    if (scrollOwners.length === 0) {
      return;
    }

    const consumed = chainWheelScroll(scrollOwners, wheelDelta);
    if (consumed) {
      event.preventDefault();
    }
  }

  root.addEventListener("wheel", handleWheel, { passive: false });

  return () => root.removeEventListener("wheel", handleWheel);
}

function normalizeWheelDelta(event: WheelEvent, root: HTMLElement): WheelDelta {
  let deltaX = event.deltaX;
  let deltaY = event.deltaY;

  if (event.shiftKey && deltaX === 0 && deltaY !== 0) {
    deltaX = deltaY;
    deltaY = 0;
  }

  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {
    return {
      deltaX: deltaX * PIXELS_PER_LINE,
      deltaY: deltaY * PIXELS_PER_LINE,
    };
  }

  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
    const pageSize = Math.max(root.clientHeight, window.innerHeight, 1);
    return {
      deltaX: deltaX * pageSize,
      deltaY: deltaY * pageSize,
    };
  }

  return { deltaX, deltaY };
}

function getScrollableWheelOwners(target: Element, root: HTMLElement): HTMLElement[] {
  const owners: HTMLElement[] = [];
  let current: Element | null = target;

  while (current && root.contains(current)) {
    if (current instanceof HTMLElement && current.matches(WHEEL_OWNER_SELECTOR) && hasScrollableAxis(current)) {
      owners.push(current);
    }

    if (current === root) {
      break;
    }

    current = current.parentElement;
  }

  return owners;
}

function hasScrollableAxis(element: HTMLElement) {
  return hasScrollableExtent(element, 'x') || hasScrollableExtent(element, 'y');
}

function chainWheelScroll(owners: HTMLElement[], wheelDelta: WheelDelta) {
  let remainingDeltaX = wheelDelta.deltaX;
  let remainingDeltaY = wheelDelta.deltaY;
  let consumed = false;

  for (const owner of owners) {
    if (remainingDeltaX !== 0 && canScroll(owner, 'x', remainingDeltaX)) {
      const movedX = scrollByDelta(owner, 'x', remainingDeltaX);
      remainingDeltaX -= movedX;
      consumed = consumed || movedX !== 0;
    }

    if (remainingDeltaY !== 0 && canScroll(owner, 'y', remainingDeltaY)) {
      const movedY = scrollByDelta(owner, 'y', remainingDeltaY);
      remainingDeltaY -= movedY;
      consumed = consumed || movedY !== 0;
    }

    if (remainingDeltaX === 0 && remainingDeltaY === 0) {
      break;
    }
  }

  return consumed;
}

function scrollByDelta(element: HTMLElement, axis: ScrollAxis, delta: number) {
  const scrollPosition = axis === 'x' ? element.scrollLeft : element.scrollTop;
  const maxScrollPosition = getMaxScrollPosition(element, axis);
  const nextScrollPosition = clamp(scrollPosition + delta, 0, maxScrollPosition);
  const moved = nextScrollPosition - scrollPosition;

  if (moved === 0) {
    return 0;
  }

  if (axis === 'x') {
    element.scrollLeft = nextScrollPosition;
  } else {
    element.scrollTop = nextScrollPosition;
  }

  return moved;
}

function canScroll(element: HTMLElement, axis: ScrollAxis, delta: number) {
  if (delta === 0 || !hasScrollableExtent(element, axis) || !hasScrollableOverflowStyle(element, axis)) {
    return false;
  }

  const currentPosition = axis === 'x' ? element.scrollLeft : element.scrollTop;
  const maxPosition = getMaxScrollPosition(element, axis);

  return delta < 0 ? currentPosition > 0 : currentPosition < maxPosition;
}

function hasScrollableExtent(element: HTMLElement, axis: ScrollAxis) {
  return getMaxScrollPosition(element, axis) > 0;
}

function getMaxScrollPosition(element: HTMLElement, axis: ScrollAxis) {
  return axis === 'x'
    ? Math.max(element.scrollWidth - element.clientWidth, 0)
    : Math.max(element.scrollHeight - element.clientHeight, 0);
}

function hasScrollableOverflowStyle(element: HTMLElement, axis: ScrollAxis) {
  const style = window.getComputedStyle(element);
  const overflow = axis === 'x' ? style.overflowX : style.overflowY;

  return overflow === 'auto' || overflow === 'scroll' || overflow === 'overlay';
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
