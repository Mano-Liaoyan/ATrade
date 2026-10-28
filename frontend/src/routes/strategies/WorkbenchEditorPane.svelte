<!-- PROTOTYPE (#99), throwaway: the editor pane of the strategy workbench. A file tab line with the panel buttons, and
     the code editor that fills the pane. A collapsed pane shows only its tab line. -->
<script lang="ts">
  import type { Extension } from '@codemirror/state';
  import { Tabs } from '#lib/foundation/carbon';
  import { CodeEditor } from '#lib/foundation/code_editor';
  import type { PanelSize } from './workbench_layout';
  import WorkbenchTabLine from './WorkbenchTabLine.svelte';

  interface Props {
    fileName: string;
    code: string;
    // The editor is created again when this changes, for example for another strategy.
    editorKey: string;
    extensions: Extension[];
    size: PanelSize;
    isCollapsed: boolean;
    onCodeChange: (code: string) => void;
    onToggleMinimized: () => void;
    onToggleMaximized: () => void;
  }

  const {
    fileName,
    code,
    editorKey,
    extensions,
    size,
    isCollapsed,
    onCodeChange,
    onToggleMinimized,
    onToggleMaximized,
  }: Props = $props();
</script>

<section class="editor-pane" aria-label="Editor">
  <WorkbenchTabLine {size} {onToggleMinimized} {onToggleMaximized}>
    <Tabs label="Files" items={[{ value: 'main', label: fileName }]} value="main" onValueChange={() => {}} />
  </WorkbenchTabLine>
  <!-- The editor stays in the page while the pane is collapsed, so it keeps the cursor and the undo history. -->
  <div class="editor-area" hidden={isCollapsed}>
    {#key editorKey}
      <CodeEditor {code} label="Strategy code" {onCodeChange} {extensions} />
    {/key}
  </div>
</section>

<style>
  .editor-pane {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    min-block-size: 0;
  }

  .editor-area {
    flex: 1;
    min-block-size: 0;
  }

  .editor-area[hidden] {
    display: none;
  }

  .editor-area :global(.code-editor) {
    border: 0;
  }
</style>
