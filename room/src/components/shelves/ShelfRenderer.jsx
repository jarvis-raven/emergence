import { useState, useEffect } from 'react';
import MemoryShelfView from './MemoryShelfView';
import GenericShelfView from './GenericShelfView';

const RENDERER_MAP = {
  memory: MemoryShelfView,
};

function ErrorFallback({ error }) {
  return (
    <div className="text-center p-4 bg-danger/10 rounded-lg">
      <span className="text-danger/80 text-sm">
        Error rendering shelf: {error?.message || 'Unknown error'}
      </span>
    </div>
  );
}

export default function ShelfRenderer({ shelf, data }) {
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
  }, [shelf?.id]);

  if (error) return <ErrorFallback error={error} />;

  if (!shelf) {
    return (
      <div className="text-center p-4 bg-background/50 rounded-lg">
        <span className="text-textMuted/50">No shelf selected</span>
      </div>
    );
  }

  const rendererName = shelf.renderer || 'auto';
  const ViewComponent = RENDERER_MAP[rendererName] || GenericShelfView;

  try {
    return <ViewComponent data={data} />;
  } catch (renderError) {
    console.error('Error rendering shelf:', renderError);
    return <ErrorFallback error={renderError} />;
  }
}
