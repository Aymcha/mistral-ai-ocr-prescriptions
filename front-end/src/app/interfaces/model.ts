export interface SelectedValue {
  value: string;
  type: 'best_match' | 'extracted' | 'modified';
}

export interface Ordonnance {
    normal_treatment: { value: string | null; confidence: number | null };
    ald_treatment: { value: string | null; confidence: number | null };
    am_finess_number: { value: string | null; confidence: number | string | null };
    best_am_finess_number: { value: string | null };
    prescriber_name: { value: string | null; confidence: number | null };
    best_prescriber_name: { value: string | null };
    prescription_date: { value: string | null; confidence: number | null };
    rpps_number: { value: string | null; confidence: number | null };
    best_rpps_number: { value: string | null};
}