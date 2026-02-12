/**
 * MobileNav — Bottom navigation for mobile devices
 * 
 * Shows on screens < 1024px. Tabs matching Room's panels.
 * Center tab (Drives) is elevated and highlighted.
 */

const tabs = [
  { id: 'mirror', icon: '🪞', label: 'Mirror' },
  { id: 'journal', icon: '📓', label: 'Journal' },
  { id: 'drives', icon: '🧠', label: 'Home' },
  { id: 'aspirations', icon: '✨', label: 'Aspirations' },
  { id: 'projects', icon: '🚀', label: 'Projects' },
]

export default function MobileNav({ activeTab, onTabChange }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-slate-950 border-t border-slate-800/50">
      <div
        className="flex justify-around items-end px-2 pt-1"
        style={{ paddingBottom: 'max(8px, env(safe-area-inset-bottom))' }}
      >
        {tabs.map(tab => {
          const active = activeTab === tab.id
          const isCenter = tab.id === 'drives'
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex flex-col items-center py-2 px-2 min-w-[44px] min-h-[44px]
                transition-all duration-200
                ${isCenter ? '-mt-3' : ''}
              `}
            >
              {/* Active indicator */}
              <div
                className={`w-8 h-0.5 rounded-full mb-1.5 transition-all duration-200 ${
                  active ? 'bg-blue-400 opacity-100' : 'opacity-0'
                }`}
              />

              {/* Icon */}
              <span
                className={`
                  transition-all duration-200
                  ${isCenter ? 'text-2xl' : 'text-xl'}
                  ${isCenter && active ? 'drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]' : ''}
                `}
              >
                {tab.icon}
              </span>

              {/* Label */}
              <span
                className={`
                  text-[10px] font-medium mt-1 transition-all duration-200
                  ${active ? 'text-blue-400' : 'text-slate-500'}
                  ${isCenter ? 'text-xs' : ''}
                `}
              >
                {tab.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
