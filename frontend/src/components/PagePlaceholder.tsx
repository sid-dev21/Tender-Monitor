interface Props {
  title: string
  description: string
  backendPhase: string
}

// Temporary content for a page whose backend endpoints don't exist yet.
// Replace the body with your Stitch design once the matching phase is built.
export function PagePlaceholder({ title, description, backendPhase }: Props) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
      <p className="mt-2 max-w-2xl text-gray-600">{description}</p>
      <div className="mt-6 rounded-lg border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-500">
        Placeholder — this screen gets wired up when{' '}
        <span className="font-medium text-gray-700">{backendPhase}</span> is built.
        Your Stitch design drops in here.
      </div>
    </div>
  )
}
