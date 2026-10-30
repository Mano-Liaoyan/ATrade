// The Compose file keeps the assistant service apart from the database, IBKR, and the secrets of .env
// (docs/architecture/assistant.md 25.2.2 and 25.3.1).
import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vite-plus/test';
import { parse } from 'yaml';

interface ComposeService {
  read_only?: boolean;
  mem_limit?: string;
  ports?: unknown[];
  env_file?: unknown;
  environment?: Record<string, string>;
  networks?: string[] | Record<string, unknown>;
  volumes?: string[];
}

interface ComposeNetwork {
  name?: string;
  internal?: boolean;
  ipam?: { config?: { subnet?: string }[] };
}

interface ComposeFile {
  services: Record<string, ComposeService>;
  networks: Record<string, ComposeNetwork>;
  volumes: Record<string, { name?: string }>;
}

const compose = parse(readFileSync(new URL('../../deploy/compose.yaml', import.meta.url), 'utf8')) as ComposeFile;
const assistant = compose.services['assistant'];

function readNetworkNames(service: ComposeService): string[] {
  const networks = service.networks ?? ['default'];
  return Array.isArray(networks) ? networks : Object.keys(networks);
}

function readMembers(network: string): string[] {
  return Object.entries(compose.services)
    .filter(([, service]) => readNetworkNames(service).includes(network))
    .map(([name]) => name)
    .sort();
}

describe('the assistant service', () => {
  test('has a read-only root file system and a memory limit of 1g by default', () => {
    expect(assistant?.read_only).toBe(true);
    expect(assistant?.mem_limit).toBe('${ATRADE_ASSISTANT_MEMORY_LIMIT:-1g}');
  });

  test('publishes no port and reads no env file', () => {
    expect(assistant?.ports).toBeUndefined();
    expect(assistant?.env_file).toBeUndefined();
  });

  test('gets no database URL, no PostgreSQL password, and no IBKR setting', () => {
    const names = Object.keys(assistant?.environment ?? {});
    const values = Object.values(assistant?.environment ?? {});

    expect(names).not.toContain('DATABASE_URL');
    expect(names.filter((name) => name.startsWith('ATRADE_IBKR_'))).toEqual([]);
    expect(values.filter((value) => /ATRADE_POSTGRES_PASSWORD|ATRADE_IBKR_|DATABASE_URL/.test(value))).toEqual([]);
  });

  test('keeps its pi files in the volume atrade-assistant-pi', () => {
    expect(assistant?.volumes).toContain('assistant-pi:/data');
    expect(compose.volumes['assistant-pi']?.name).toBe('atrade-assistant-pi');
  });
});

describe('the assistant networks', () => {
  test('atrade-assistant-internal is internal, has a fixed subnet, and has only web and assistant', () => {
    const network = compose.networks['assistant-internal'];

    expect(network?.name).toBe('atrade-assistant-internal');
    expect(network?.internal).toBe(true);
    expect(network?.ipam?.config?.[0]?.subnet).toMatch(/^\d+\.\d+\.\d+\.\d+\/\d+$/);
    expect(readMembers('assistant-internal')).toEqual(['assistant', 'web']);
  });

  test('atrade-assistant-egress is not internal and has only assistant', () => {
    const network = compose.networks['assistant-egress'];

    expect(network?.name).toBe('atrade-assistant-egress');
    expect(network?.internal).not.toBe(true);
    expect(readMembers('assistant-egress')).toEqual(['assistant']);
  });

  test('assistant shares no network with postgres or ib-gateway', () => {
    const assistantNetworks = readNetworkNames(assistant ?? {});

    for (const service of ['postgres', 'ib-gateway']) {
      const shared = readNetworkNames(compose.services[service] ?? {}).filter((name) => assistantNetworks.includes(name));
      expect(shared).toEqual([]);
    }
  });
});
