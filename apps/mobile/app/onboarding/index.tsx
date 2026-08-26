/**
 * apps/mobile/app/onboarding/index.tsx
 *
 * 3-Step Adaptive Medical Onboarding Wizard for Mobile.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  TextInput,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  Microscope,
  GraduationCap,
  Stethoscope,
  Building2,
  Award,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
} from 'lucide-react-native';
import { useAuth } from '../../lib/auth/auth-context';
import { studentApi } from '@medical/api-client';
import { ExaminationNode, MedicalTaxonomyMetadata } from '@medical/shared';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export default function OnboardingScreen() {
  const router = useRouter();
  const { user, updateProfile } = useAuth();

  const [step, setStep] = useState(1);
  const [taxonomy, setTaxonomy] = useState<MedicalTaxonomyMetadata | null>(null);

  const [targetExam, setTargetExam] = useState(user?.target_exam || 'NEET_SS');
  const [targetYear, setTargetYear] = useState<number>(user?.target_year || 2026);
  const [primarySpeciality, setPrimarySpeciality] = useState(user?.primary_speciality || 'Oncopathology');
  const [residencyStage, setResidencyStage] = useState(user?.residency_stage || 'JR');
  const [medicalCollege, setMedicalCollege] = useState(user?.medical_college || '');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    studentApi
      .getTaxonomies()
      .then((data) => {
        setTaxonomy(data);
        const currentExam = data.examinations.find((e) => e.id === (user?.target_exam || 'NEET_SS'));
        if (currentExam) {
          if (!currentExam.has_specialities && currentExam.default_speciality) {
            setPrimarySpeciality(currentExam.default_speciality);
          } else if (currentExam.specialities && currentExam.specialities.length > 0 && !user?.primary_speciality) {
            const firstSpec = currentExam.specialities[0]?.id;
            if (firstSpec) setPrimarySpeciality(firstSpec);
          }
        }
      })
      .catch((err) => console.warn('Taxonomies load note:', err));
  }, [user]);

  const examinations: ExaminationNode[] = taxonomy?.examinations || [
    {
      id: 'NEET_SS',
      title: 'NEET-SS / DrNB Super-Specialty',
      badge: 'Super-Specialty',
      category: 'super_specialty',
      description: 'Oncology, sub-specialty IHC algorithms, flow cytometry & molecular diagnostics.',
      has_specialities: true,
      specialities: [
        { id: 'Oncopathology', name: 'Oncopathology & Tumor Markers' },
        { id: 'Hematopathology', name: 'Hematopathology & Flow Cytometry' },
        { id: 'General & Surgical Pathology', name: 'General & Surgical Pathology' },
        { id: 'Molecular Diagnostics', name: 'Molecular Diagnostics & IHC' },
      ],
    },
    {
      id: 'MD_PATH',
      title: 'MD / MS / DNB Residency Exit',
      badge: 'Residency Exit',
      category: 'postgraduate',
      description: 'Comprehensive surgical pathology, hematology, and clinical diagnostics.',
      has_specialities: true,
      specialities: [
        { id: 'General & Surgical Pathology', name: 'General & Surgical Pathology' },
        { id: 'Hematopathology', name: 'Clinical Hematology & Transfusion' },
        { id: 'Cytopathology', name: 'Diagnostic Cytopathology' },
      ],
    },
    {
      id: 'NEET_PG',
      title: 'NEET-PG / INI-CET Entrance',
      badge: 'Entrance',
      category: 'postgraduate',
      description: 'High-yield clinical vignettes with strong pathology core foundation.',
      has_specialities: false,
      default_speciality: 'General Medicine & Pathology Core',
      specialities: [],
    },
    {
      id: 'MBBS',
      title: 'MBBS Professional University Exam',
      badge: 'Undergraduate',
      category: 'undergraduate',
      description: 'Core general & systemic pathology disease mechanisms.',
      has_specialities: false,
      default_speciality: '2nd Professional Pathology Core',
      specialities: [],
    },
    {
      id: 'FELLOWSHIP',
      title: 'Post-Doctoral Clinical Fellowship',
      badge: 'Fellowship',
      category: 'fellowship',
      description: 'Tata / AIIMS sub-specialty pattern fellowships.',
      has_specialities: true,
      specialities: [
        { id: 'Oncopathology Fellowship', name: 'Oncopathology Fellowship' },
        { id: 'Hematopathology Fellowship', name: 'Hematopathology Fellowship' },
      ],
    },
  ];

  const selectedExamNode = examinations.find((e) => e.id === targetExam) || examinations[0];

  const handleSelectExam = (examId: string) => {
    setTargetExam(examId);
    const exam = examinations.find((e) => e.id === examId);
    if (exam) {
      if (!exam.has_specialities && exam.default_speciality) {
        setPrimarySpeciality(exam.default_speciality);
      } else if (exam.specialities && exam.specialities.length > 0) {
        const firstSpec = exam.specialities[0]?.id;
        if (firstSpec) setPrimarySpeciality(firstSpec);
      }
    }
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      const updated = await studentApi.updateOnboarding({
        target_exam: targetExam,
        target_year: targetYear,
        residency_stage: residencyStage,
        medical_college: medicalCollege.trim() || 'Medical College',
        primary_speciality: primarySpeciality,
      });
      updateProfile(updated);
      router.replace('/(tabs)' as any);
    } catch (err) {
      console.error('Failed to complete onboarding:', err);
      router.replace('/(tabs)' as any);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Progress header */}
        <View style={styles.progressHeader}>
          <Text style={styles.stepCounter}>Step {step} of 3</Text>
          <View style={styles.progressBarBg}>
            <View style={[styles.progressBarFill, { width: `${(step / 3) * 100}%` }]} />
          </View>
        </View>

        {/* STEP 1: Target Medical Exam */}
        {step === 1 && (
          <View style={styles.stepContainer}>
            <View style={styles.stepTitleRow}>
              <Sparkles size={16} color="#38bdf8" />
              <Text style={styles.stepBadge}>Step 1: Examination</Text>
            </View>
            <Text style={styles.stepHeading}>What exam are you preparing for?</Text>
            <Text style={styles.stepSubheading}>
              Select your examination level to calibrate blueprint mock engines.
            </Text>

            <View style={styles.optionList}>
              {examinations.map((ex) => {
                const isSelected = targetExam === ex.id;
                return (
                  <TouchableOpacity
                    key={ex.id}
                    activeOpacity={0.75}
                    onPress={() => handleSelectExam(ex.id)}
                    style={[styles.examCard, isSelected ? styles.examCardSelected : null]}
                  >
                    <View style={styles.examCardHeader}>
                      <Text style={[styles.examCardTitle, isSelected ? styles.textSky : null]}>
                        {ex.title}
                      </Text>
                      {isSelected ? <CheckCircle2 size={18} color="#38bdf8" /> : null}
                    </View>
                    <Text style={styles.examCardDesc}>{ex.description}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <Button
              title="Continue to Speciality"
              variant="primary"
              size="lg"
              onPress={() => setStep(2)}
              icon={<ArrowRight size={16} color="#ffffff" />}
              style={{ marginTop: 20 }}
            />
          </View>
        )}

        {/* STEP 2: Speciality & Target Year */}
        {step === 2 && (
          <View style={styles.stepContainer}>
            <View style={styles.stepTitleRow}>
              <Sparkles size={16} color="#38bdf8" />
              <Text style={styles.stepBadge}>Step 2: Speciality & Attempt</Text>
            </View>
            <Text style={styles.stepHeading}>Choose your curriculum track</Text>
            <Text style={styles.stepSubheading}>
              {selectedExamNode.has_specialities
                ? 'Select your target specialty leaf node for dedicated high-yield question drills.'
                : `This examination uses the unified core curriculum (${selectedExamNode.default_speciality}).`}
            </Text>

            {selectedExamNode.has_specialities && selectedExamNode.specialities ? (
              <View style={styles.optionList}>
                {selectedExamNode.specialities.map((sp) => {
                  const isSelected = primarySpeciality === sp.id;
                  return (
                    <TouchableOpacity
                      key={sp.id}
                      activeOpacity={0.75}
                      onPress={() => setPrimarySpeciality(sp.id)}
                      style={[styles.specCard, isSelected ? styles.examCardSelected : null]}
                    >
                      <Text style={[styles.specTitle, isSelected ? styles.textSky : null]}>
                        {sp.name}
                      </Text>
                      {isSelected ? <CheckCircle2 size={16} color="#38bdf8" /> : null}
                    </TouchableOpacity>
                  );
                })}
              </View>
            ) : null}

            {/* Target Year */}
            <Text style={[styles.inputLabel, { marginTop: 16 }]}>Target Exam Attempt Year</Text>
            <View style={styles.yearRow}>
              {[2026, 2027, 2028].map((yr) => (
                <TouchableOpacity
                  key={yr}
                  onPress={() => setTargetYear(yr)}
                  style={[styles.yearPill, targetYear === yr ? styles.yearPillActive : null]}
                >
                  <Text style={[styles.yearText, targetYear === yr ? styles.textSky : null]}>
                    {yr}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.btnRow}>
              <Button
                title="Back"
                variant="outline"
                size="md"
                onPress={() => setStep(1)}
                icon={<ArrowLeft size={16} color="#38bdf8" />}
                style={{ flex: 1, marginRight: 8 }}
              />
              <Button
                title="Next"
                variant="primary"
                size="md"
                onPress={() => setStep(3)}
                icon={<ArrowRight size={16} color="#ffffff" />}
                style={{ flex: 1, marginLeft: 8 }}
              />
            </View>
          </View>
        )}

        {/* STEP 3: Experience & College */}
        {step === 3 && (
          <View style={styles.stepContainer}>
            <View style={styles.stepTitleRow}>
              <Sparkles size={16} color="#38bdf8" />
              <Text style={styles.stepBadge}>Step 3: Clinical Profile</Text>
            </View>
            <Text style={styles.stepHeading}>Your Medical Experience</Text>
            <Text style={styles.stepSubheading}>
              Calibrates adaptive distractor complexity and explanations.
            </Text>

            <View style={styles.optionList}>
              {[
                { id: 'MBBS', label: 'MBBS Student / Intern' },
                { id: 'JR', label: 'Junior Resident (MD / MS Trainee)' },
                { id: 'SR', label: 'Senior Resident (Post-MD / Post-MS)' },
                { id: 'FELLOW', label: 'Sub-Specialty Fellow' },
                { id: 'CONSULTANT', label: 'Consultant / Specialist' },
              ].map((st) => {
                const isSelected = residencyStage === st.id;
                return (
                  <TouchableOpacity
                    key={st.id}
                    activeOpacity={0.75}
                    onPress={() => setResidencyStage(st.id)}
                    style={[styles.specCard, isSelected ? styles.examCardSelected : null]}
                  >
                    <Text style={[styles.specTitle, isSelected ? styles.textSky : null]}>
                      {st.label}
                    </Text>
                    {isSelected ? <CheckCircle2 size={16} color="#38bdf8" /> : null}
                  </TouchableOpacity>
                );
              })}
            </View>

            <Text style={[styles.inputLabel, { marginTop: 16 }]}>Medical College / Hospital (Optional)</Text>
            <TextInput
              style={styles.collegeInput}
              placeholder="e.g. AIIMS New Delhi / CMC Vellore"
              placeholderTextColor="#64748b"
              value={medicalCollege}
              onChangeText={setMedicalCollege}
            />

            <View style={styles.btnRow}>
              <Button
                title="Back"
                variant="outline"
                size="md"
                onPress={() => setStep(2)}
                icon={<ArrowLeft size={16} color="#38bdf8" />}
                style={{ flex: 1, marginRight: 8 }}
              />
              <Button
                title="Launch Dashboard"
                variant="primary"
                size="md"
                loading={loading}
                onPress={handleFinish}
                style={{ flex: 1, marginLeft: 8 }}
              />
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#020617',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  progressHeader: {
    marginBottom: 24,
  },
  stepCounter: {
    fontSize: 12,
    fontWeight: '700',
    color: '#94a3b8',
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  progressBarBg: {
    height: 6,
    backgroundColor: '#1e293b',
    borderRadius: 999,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#0284c7',
    borderRadius: 999,
  },
  stepContainer: {
    backgroundColor: '#0f172a',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 20,
  },
  stepTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  stepBadge: {
    fontSize: 12,
    fontWeight: '700',
    color: '#38bdf8',
    textTransform: 'uppercase',
  },
  stepHeading: {
    fontSize: 22,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: -0.4,
    marginBottom: 6,
  },
  stepSubheading: {
    fontSize: 13,
    color: '#94a3b8',
    lineHeight: 18,
    marginBottom: 18,
  },
  optionList: {
    gap: 10,
  },
  examCard: {
    backgroundColor: '#020617',
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: '#334155',
    padding: 14,
  },
  examCardSelected: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(2, 132, 199, 0.12)',
  },
  examCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  examCardTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
  },
  examCardDesc: {
    fontSize: 11,
    color: '#94a3b8',
    lineHeight: 16,
  },
  specCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#020617',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#334155',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  specTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#cbd5e1',
    marginBottom: 8,
  },
  yearRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 16,
  },
  yearPill: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#020617',
    borderWidth: 1.5,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  yearPillActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
  },
  yearText: {
    fontSize: 15,
    fontWeight: '800',
    color: '#94a3b8',
  },
  collegeInput: {
    backgroundColor: '#020617',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#334155',
    height: 48,
    paddingHorizontal: 14,
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 20,
  },
  btnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  textSky: {
    color: '#38bdf8',
  },
});
