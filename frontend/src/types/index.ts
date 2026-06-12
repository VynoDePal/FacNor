export interface User {
  id: number;
  username: string;
  email: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  address: string;
  phone: string;
  siren: string;
  tva_number: string;
  is_company: boolean;
}

export interface Invoice {
  id: number;
  client_id: number;
  invoice_number: string;
  date_issued: string;
  date_due?: string;
  status: string;
  notes?: string;
  lines: InvoiceLine[];
  total_ht: number;
  total_vat: number;
  total_ttc: number;
}

export interface InvoiceLine {
  id?: number;
  description: string;
  quantity: number;
  unit_price_ht: number;
  vat_rate: number;
}
