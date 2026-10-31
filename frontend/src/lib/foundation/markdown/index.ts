// Public entry of foundation/markdown: the Markdown component for untrusted markdown text, such as the messages of the
// AI assistant (docs/architecture/assistant.md 25.12.6). marked reads the text; @pierre/diffs (syntax colors and diff
// view) and pele (Mermaid diagrams) load only when a block needs them.
import './markdown.scss';

export { default as Markdown } from './Markdown.svelte';
