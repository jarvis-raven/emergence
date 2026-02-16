/**
 * Horizontal tab bar for shelf navigation
 */
export default function ShelfTabs({ shelves, activeId, onSelect }) {
  if (!shelves || shelves.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-1 border-b border-surface overflow-x-auto">
      {shelves.map((shelf) => {
        const isActive = shelf.id === activeId;
        return (
          <button
            key={shelf.id}
            onClick={() => onSelect(shelf.id)}
            className={`
              flex items-center gap-2 px-3 py-2 text-sm whitespace-nowrap
              transition-colors focus:outline-none
              ${
                isActive
                  ? 'border-b-2 border-primary text-text font-medium'
                  : 'border-b-2 border-transparent text-textMuted hover:text-text'
              }
            `}
          >
            {shelf.icon && <span>{shelf.icon}</span>}
            <span>{shelf.name}</span>
          </button>
        );
      })}
    </div>
  );
}
