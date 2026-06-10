export interface LigneFacture {
  id?: number;
  description: string;
  quantite: number;
  prix_unitaire: number;
  montant_ht: number;
  tva_taux: number;
  montant_tva: number;
  montant_ttc: number;
}

export interface Facture {
  id: number;
  numero: string;
  client_id: number;
  date_facture: string;
  date_echeance: string;
  statut: string;
  notes?: string;
  lignes: LigneFacture[];
}

export interface FactureCreate {
  numero?: string;
  client_id: number;
  date_facture: string;
  date_echeance: string;
  statut: string;
  notes?: string;
  lignes: LigneFacture[];
}

export interface FactureUpdate {
  numero?: string;
  client_id?: number;
  date_facture?: string;
  date_echeance?: string;
  statut?: string;
  notes?: string;
  lignes?: LigneFacture[];
}
