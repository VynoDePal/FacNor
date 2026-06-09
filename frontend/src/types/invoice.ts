export interface InvoiceLine {
  id?: number;
  description: string;
  quantity: number;
  unit_price_ht: number;
  tva_rate: number;
  total_ht: number;
}

export interface InvoiceLineCreate {
  description: string;
  quantity: number;
  unit_price_ht: number;
  tva_rate: number;
  total_ht: number;
}

export interface Invoice {
  id?: number;
  invoice_number?: string;
  issue_date?: string;
  due_date?: string;
  client_id: number;
  total_ht: number;
  total_tva: number;
  total_ttc: number;
  status: string;
  lines: InvoiceLine[];
}

export interface InvoiceCreate {
  invoice_number?: string;
  issue_date?: string;
  due_date?: string;
  client_id: number;
  total_ht: number;
  total_tva: number;
  total_ttc: number;
  status: string;
  lines: InvoiceLineCreate[];
}
