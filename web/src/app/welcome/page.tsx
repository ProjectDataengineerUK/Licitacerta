"use client";
import { useState } from "react";
import { WizardShell } from "@/components/wizard/WizardShell";
import { WizardStep1 } from "@/components/wizard/WizardStep1";
import { WizardStep2 } from "@/components/wizard/WizardStep2";
import { WizardStep3 } from "@/components/wizard/WizardStep3";

export default function WelcomePage() {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<Record<string, unknown>>({});

  const steps = [
    <WizardStep1
      key={1}
      onNext={(d) => {
        setData((p) => ({ ...p, ...d }));
        setStep(2);
      }}
    />,
    <WizardStep2
      key={2}
      onBack={() => setStep(1)}
      onNext={(d) => {
        setData((p) => ({ ...p, ...d }));
        setStep(3);
      }}
    />,
    <WizardStep3 key={3} onBack={() => setStep(2)} wizardData={data} />,
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <WizardShell step={step} totalSteps={3}>
        {steps[step - 1]}
      </WizardShell>
    </div>
  );
}
