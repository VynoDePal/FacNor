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
  number: string;
  date: string;
  items: InvoiceItem[];
  total_ht: number;
  total_tva: number;
  total_ttc: number;
}

export interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  tva_rate: number;
  total_ht?: number;
  total_ttc?: number;
}
