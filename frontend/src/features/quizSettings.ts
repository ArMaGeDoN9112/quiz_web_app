export function orderQuizItems<T>(
  items: readonly T[],
  shouldShuffle: boolean,
  random: () => number = Math.random,
): T[] {
  const orderedItems = [...items]
  if (!shouldShuffle) return orderedItems

  for (let index = orderedItems.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(random() * (index + 1))
    const item = orderedItems[index]
    orderedItems[index] = orderedItems[randomIndex]
    orderedItems[randomIndex] = item
  }
  return orderedItems
}
