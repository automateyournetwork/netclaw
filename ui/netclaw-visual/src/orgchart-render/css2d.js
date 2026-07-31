/**
 * CSS2D label DOM cleanup.
 *
 * A CSS2DObject only removes its own <div> when THAT OBJECT is removed from its
 * parent. Removing a whole GROUP that contains labels does not fire per-label
 * cleanup, so every label element inside it stays in the document — orphaned,
 * frozen at its last projected screen position, while the live chart continues
 * to pan underneath it. On screen that reads as "a second copy of the chart
 * that doesn't move".
 *
 * Any dispose() that tears down a group containing labels must call this.
 * See also expansion.js collapse(), which has always done this by hand.
 */
export function removeLabelElements(group) {
  group?.traverse?.((object) => {
    if (object?.element?.remove) object.element.remove();
  });
}
