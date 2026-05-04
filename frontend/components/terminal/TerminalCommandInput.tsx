"use client";

import { FormEvent, useId, useState } from "react";

import { parseTerminalCommand, TERMINAL_COMMAND_HELP } from "@/lib/terminalCommandRegistry";
import type { TerminalCommandParseResult } from "@/types/terminal";

type TerminalCommandInputProps = {
  feedback?: string;
  onCommand: (result: TerminalCommandParseResult) => void;
};

export function TerminalCommandInput({ feedback, onCommand }: TerminalCommandInputProps) {
  const [commandText, setCommandText] = useState("");
  const inputId = useId();
  const helpId = `${inputId}-help`;
  const feedbackId = `${inputId}-feedback`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = parseTerminalCommand(commandText);
    onCommand(result);

    if (result.ok) {
      setCommandText("");
    }
  }

  return (
    <form className="terminal-command-input" data-testid="terminal-command-input" onSubmit={handleSubmit}>
      <label className="terminal-command-input__label" htmlFor={inputId}>
        Command
      </label>
      <div className="terminal-command-input__control">
        <span aria-hidden="true" className="terminal-command-input__prompt">
          AT&gt;
        </span>
        <input
          aria-describedby={`${helpId} ${feedbackId}`}
          autoCapitalize="characters"
          autoComplete="off"
          className="terminal-command-input__field"
          id={inputId}
          inputMode="text"
          placeholder="HOME · SEARCH AAPL · CHART MSFT · HELP"
          spellCheck={false}
          type="text"
          value={commandText}
          onChange={(event) => setCommandText(event.target.value)}
        />
        <button className="terminal-command-input__submit" type="submit">
          Run
        </button>
      </div>
      <p className="terminal-command-input__help" id={helpId}>
        {TERMINAL_COMMAND_HELP}
      </p>
      <p aria-live="polite" className="terminal-command-input__feedback" id={feedbackId} role="status">
        {feedback ?? "Deterministic local commands only; no natural-language routing or broker submission."}
      </p>
    </form>
  );
}
