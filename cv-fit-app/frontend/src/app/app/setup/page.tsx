"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useWorkspace } from "@/context/WorkspaceContext";
import InputSection from "@/components/workspace/InputSection";

export default function SetupPage() {
  const router = useRouter();
  const { cvText, jdText, updateWorkspace } = useWorkspace();

  // Local form state initialized from context
  const [localInputs, setLocalInputs] = useState({
    cvText: cvText,
    jdText: jdText,
    cvFile: null as File | null,
    jdFile: null as File | null,
  });
  
  const [error, setError] = useState("");

  const handleInputChange = (patch: Partial<typeof localInputs>) => {
    setLocalInputs(prev => ({ ...prev, ...patch }));
  };

  const handleSaveAndNavigate = (targetRoute: string) => {
    if (!localInputs.cvText.trim()) { 
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!"); 
      return; 
    }
    setError("");

    // Save to global context
    updateWorkspace({
      cvText: localInputs.cvText,
      cvFileName: localInputs.cvFile ? localInputs.cvFile.name : "CV của tôi",
      jdText: localInputs.jdText || "",
    });

    // Navigate to the chosen tool
    router.push(targetRoute);
  };

  return (
    <div className="h-full">
      <InputSection 
        inputs={localInputs}
        onChange={handleInputChange}
        onAnalyze={() => handleSaveAndNavigate("/app/analyzer")}
        onInterview={() => handleSaveAndNavigate("/app/interview")}
        onWrite={() => handleSaveAndNavigate("/app/writer")}
        onSearchJobs={() => handleSaveAndNavigate("/app/jobs")}
        isAnalyzing={false}
        isStartingInterview={false}
        isWriting={false}
        error={error}
      />
    </div>
  );
}
