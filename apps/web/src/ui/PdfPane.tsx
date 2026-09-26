/**
 * The reference, beside the grid.
 *
 * An <iframe> and the browser's own PDF viewer, nothing more. lothype.com
 * sends neither X-Frame-Options nor a CSP, so its PDFs embed as they are; a
 * page that refuses will show its refusal in the frame, and the link above it
 * still opens the thing in a tab. Rendering PDFs ourselves would mean fetching
 * them, which the same site does not allow cross-origin.
 */
export const PdfPane = ({ url }: { url: string }) => {
  if (!url.trim()) {
    return (
      <aside className="pdf empty-pane">
        <div className="empty">Pas de référence. Renseigne un lien vers un PDF pour l’afficher ici.</div>
      </aside>
    )
  }
  return (
    <aside className="pdf">
      <div className="pdf-bar">
        <span>référence</span>
        <a href={url} target="_blank" rel="noreferrer">ouvrir dans un onglet</a>
      </div>
      <iframe title="référence" src={url} />
    </aside>
  )
}
