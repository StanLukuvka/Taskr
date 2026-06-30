// FLOW-PRODUCED: 2026-06-30_m2-flows-workbench.md
import { createBrowserRouter } from 'react-router';
import App from './App';
import { IntegrationsListView } from './components/bindings/IntegrationsListView';
import { IntegrationDetailView } from './components/bindings/IntegrationDetailView';
import { RunsListView } from './components/runs/RunsListView';
import { FlowsListView } from './components/flows/FlowsListView';
import { FlowDetailView } from './components/flows/FlowDetailView';
import { WorkbenchView } from './components/workbench/WorkbenchView';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <RunsListView /> },
      { path: 'runs', element: <RunsListView /> },
      { path: 'runs/:runId', element: <WorkbenchView /> },
      { path: 'flows', element: <FlowsListView /> },
      { path: 'flows/:slug', element: <FlowDetailView /> },
      { path: 'integrations', element: <IntegrationsListView /> },
      { path: 'integrations/:integrationId', element: <IntegrationDetailView /> },
      {
        path: '*',
        element: (
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-foreground">404</h1>
            <p className="text-muted-foreground">This page doesn't exist.</p>
          </div>
        ),
      },
    ],
  },
]);
