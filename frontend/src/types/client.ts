export interface Client {
  id: number;
  name: string;
  email?: string;
  address?: string;
  vat_number?: string;
  siren?: string;
  created_at?: string;
}

export interface ClientCreate {
  name: string;
  email?: string;
  address?: string;
  vat_number?: string;
  siren?: string;
}

export interface ClientUpdate extends Partial<ClientCreate> {}
