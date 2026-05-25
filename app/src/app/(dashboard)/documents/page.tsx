export default function DocumentsPage() {
  return (
    <div className="bg-surface-strong border border-border-light rounded-xl shadow-sm p-6">
      <span className="text-xs font-semibold text-text-secondary tracking-wide block mb-2">
        Document vault
      </span>
      <h3 className="text-lg font-bold text-text-primary mb-3">
        Encrypted uploads belong behind backend-issued workflows.
      </h3>
      <p className="text-sm text-text-secondary">
        Use this area for vault browsing, upload states, and file-level access
        rules once the API contracts are in place.
      </p>
    </div>
  );
}
