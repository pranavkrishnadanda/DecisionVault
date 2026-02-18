interface RetryPanelProps {
  title: string;
  message: string;
  onRetry: () => void;
  ctaLabel: string;
}

export function RetryPanel({
  title,
  message,
  onRetry,
  ctaLabel,
}: RetryPanelProps) {
  return (
    <div className="rounded-xl border border-red-300/50 bg-red-50 p-4 text-red-900">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-1 text-sm">{message}</p>
      <button
        className="mt-3 rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white"
        onClick={onRetry}
        type="button"
      >
        {ctaLabel}
      </button>
    </div>
  );
}
