import { TerminalRoutePage } from '@/components/terminal/TerminalRoutePage';
import type { TerminalRouteSearchParams } from '@/lib/terminalRoutes';

type TerminalPageProps = {
  searchParams?: Promise<TerminalRouteSearchParams>;
};

export default async function HelpPage({ searchParams }: TerminalPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {};

  return <TerminalRoutePage moduleId="HELP" searchParams={resolvedSearchParams} />;
}
