export type BrokerCapabilities = {
  supportsSessionStatus: boolean;
  supportsBrokerOrderPlacement: boolean;
  supportsCredentialPersistence: boolean;
  supportsExecutionPersistence: boolean;
  usesOfficialApisOnly: boolean;
};

export type BrokerStatus = {
  provider: string;
  state: string;
  mode: string;
  integrationEnabled: boolean;
  hasPaperAccountId: boolean;
  authenticated: boolean;
  connected: boolean;
  competing: boolean;
  message: string | null;
  observedAtUtc: string;
  capabilities: BrokerCapabilities;
};
