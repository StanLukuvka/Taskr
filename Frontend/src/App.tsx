// FLOW-PRODUCED: 2026-06-30_m1-visual-cleanup.md
import { NavLink, Outlet } from 'react-router';
import { TaskrIcon } from '../taskr-icon-kit/react/TaskrIcon';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { label: 'Runs', to: '/runs' },
  { label: 'Flows', to: '/flows' },
  { label: 'Integrations', to: '/integrations' },
  { label: 'Budget', to: '/budget' },
];

export default function App() {
  return (
    <div className="min-h-screen bg-bg-1 text-text">
      {/* Header */}
      <header className="flex h-12 items-center gap-6 border-b border-border bg-bg-2 px-6">
        <div className="flex items-center gap-2">
          <TaskrIcon name="taskr" className="h-6 w-6 text-accent" title="Taskr" />
          <span className="font-semibold text-accent">Taskr</span>
        </div>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={false}
              className={({ isActive }) =>
                cn(
                  'px-3 py-1.5 text-sm transition-colors',
                  isActive
                    ? 'bg-bg-3 text-accent'
                    : 'text-text-muted hover:bg-bg-3 hover:text-text',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      {/* Main content */}
      <main>
        <Outlet />
      </main>
    </div>
  );
}
