import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const DEFAULT_TAXONOMIES = {
  examinations: [
    {
      id: 'NEET_SS',
      title: 'NEET-SS / DrNB Super-Specialty',
      badge: 'Super-Specialty',
      category: 'super_specialty',
      description: 'High-yield oncology, sub-specialty IHC algorithms, flow cytometry & molecular diagnostics.',
      has_specialities: true,
      specialities: [
        {
          id: 'Oncopathology',
          name: 'Oncopathology & Tumor Markers',
          is_default: true,
          description: 'Solid tumors, WHO classifications, theranostic IHC & molecular biomarkers.',
        },
        {
          id: 'Hematopathology',
          name: 'Hematopathology & Flow Cytometry',
          description: 'Leukemias, lymphomas, bone marrow pathology & immunophenotyping.',
        },
        {
          id: 'Neuropathology',
          name: 'Neuropathology & CNS Tumors',
          description: 'CNS neoplasia, WHO CNS5 molecular entities, neuro-degenerative pathology.',
        },
        {
          id: 'Nephropathology',
          name: 'Nephropathology & Renal Biopsies',
          description: 'Glomerular diseases, transplant pathology, immunofluorescence.',
        },
        {
          id: 'Cytopathology',
          name: 'Cytopathology & FNAC',
          description: 'Bethesda systems, Paris system, Milan system, serous effusions.',
        },
        {
          id: 'Molecular Diagnostics',
          name: 'Molecular Diagnostics & Precision Oncology',
          description: 'NGS mutation panels, FISH translocations, liquid biopsies.',
        },
      ],
    },
    {
      id: 'MD_PATH',
      title: 'MD / MS / DNB Residency Exit Exam',
      badge: 'Residency Exit',
      category: 'postgraduate',
      description: 'Comprehensive postgraduate surgical pathology, hematology, autopsy & clinical pathology.',
      has_specialities: true,
      specialities: [
        {
          id: 'General & Surgical Pathology',
          name: 'General & Surgical Pathology',
          is_default: true,
          description: 'Core systemic surgical pathology, grossing protocols, diagnostic IHC.',
        },
        {
          id: 'Hematopathology',
          name: 'Clinical Hematology & Transfusion Medicine',
          description: 'Coagulation, blood banking, flow cytometry, hemoglobinopathies.',
        },
        {
          id: 'Cytopathology',
          name: 'Diagnostic Cytology & Exfoliative Smears',
          description: 'Pap smears, thyroid FNA, fluid cytology, cell blocks.',
        },
        {
          id: 'Chemical Pathology',
          name: 'Clinical Biochemistry & Lab Management',
          description: 'QC charts, automated analyzers, reference ranges.',
        },
      ],
    },
    {
      id: 'NEET_PG',
      title: 'NEET-PG / INI-CET Entrance',
      badge: 'Postgraduate Entrance',
      category: 'postgraduate',
      description: 'Comprehensive clinical vignettes across 19 subjects with deep pathology & medicine core.',
      has_specialities: false,
      default_speciality: 'General Medicine & Pathology Core',
      specialities: [],
    },
    {
      id: 'MBBS',
      title: 'MBBS Professional University Exam',
      badge: 'Undergraduate',
      category: 'undergraduate',
      description: 'Undergraduate disease mechanisms, systemic pathology & clinical vignettes.',
      has_specialities: false,
      default_speciality: '2nd Professional Pathology',
      specialities: [],
    },
    {
      id: 'FELLOWSHIP',
      title: 'Post-Doctoral Clinical Fellowship',
      badge: 'Sub-Specialty Board',
      category: 'fellowship',
      description: 'Advanced subspecialty certification in oncopathology, hematopathology, or neuropathology.',
      has_specialities: true,
      specialities: [
        {
          id: 'Oncopathology Fellowship',
          name: 'Oncopathology Fellowship (Tata / AIIMS Pattern)',
          is_default: true,
        },
        {
          id: 'Hematopathology Fellowship',
          name: 'Hematopathology & Flow Cytometry Fellowship',
        },
        {
          id: 'Dermatopathology Fellowship',
          name: 'Dermatopathology & Skin Biopsy Fellowship',
        },
      ],
    },
  ],
  experience_stages: [
    { id: 'MBBS', label: 'MBBS Student / Intern' },
    { id: 'JR', label: 'Junior Resident (MD / MS / DNB Trainee)' },
    { id: 'SR', label: 'Senior Resident (Post-MD / Post-MS)' },
    { id: 'FELLOW', label: 'Post-Doctoral Fellow' },
    { id: 'CONSULTANT', label: 'Practicing Specialist / Consultant' },
  ],
  target_years: [2026, 2027, 2028],
  metadata_version: '1.1.0',
};

export async function GET() {
  const targetUrl = `${BACKEND_URL}/api/student/taxonomies`;

  try {
    const res = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, { status: 200 });
    }
  } catch (err) {
    // If backend is offline or loading, return default taxonomies
  }

  return NextResponse.json(DEFAULT_TAXONOMIES, { status: 200 });
}
