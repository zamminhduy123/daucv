"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { LayoutLine } from "@/types";
import { useWorkspace } from "@/context/WorkspaceContext";
import InputSection from "@/components/workspace/InputSection";

interface LocalInputsState {
  cvText: string;
  jdText: string;
  cvFile: File | null;
  jdFile: File | null;
  layoutData: LayoutLine[] | null;
}

export default function SetupPage() {
  const router = useRouter();
  const {
    cvText,
    cvFileName,
    jdText,
    layoutData: workspaceLayoutData,
    updateWorkspace,
    uploadFileCV,
    deleteActiveCV,
  } = useWorkspace();

  // Local form state initialized from context
  const [localInputs, setLocalInputs] = useState<LocalInputsState>({
    cvText: cvText,
    jdText: jdText,
    cvFile: null,
    jdFile: null,
    layoutData: workspaceLayoutData,
  });
  
  const [error, setError] = useState("");

  // Sync state if context loads asynchronously (e.g. from DB)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocalInputs((prev) => {
      const mockFile = cvText && cvFileName && cvFileName !== "CV của tôi"
        ? new File([], cvFileName, { type: "application/pdf" })
        : prev.cvFile;
      return {
        cvText,
        jdText,
        cvFile: mockFile,
        jdFile: prev.jdFile,
        layoutData: workspaceLayoutData,
      };
    });
  }, [cvText, jdText, cvFileName, workspaceLayoutData]);

  const handleInputChange = (patch: Partial<LocalInputsState>) => {
    setLocalInputs(prev => ({ ...prev, ...patch }));

    // Auto-save CV upload/change to DB
    if (patch.cvText !== undefined) {
      if (!patch.cvText.trim() || patch.cvFile === null) {
        deleteActiveCV();
      } else if (patch.cvFile && patch.cvFile !== localInputs.cvFile) {
        // This is a fresh file upload! Trigger historical row creation in the DB
        uploadFileCV(patch.cvText, patch.cvFile.name);
      } else {
        // This is a normal text area edit! Update the text context (triggers debounced update in place)
        updateWorkspace({
          cvText: patch.cvText,
          cvFileName: patch.cvFile ? patch.cvFile.name : cvFileName,
        });
      }
    }

    // Sync layoutData to workspace locally (enables layout-aware reconstruction)
    if (patch.layoutData !== undefined) {
      updateWorkspace({ layoutData: patch.layoutData });
    }

    // Sync JD text to workspace locally
    if (patch.jdText !== undefined) {
      updateWorkspace({ jdText: patch.jdText });
    }
  };

  const handleSaveAndNavigate = (targetRoute: string) => {
    if (!localInputs.cvText.trim()) { 
      setError("Bạn chưa có nội dung CV — dán text hoặc tải PDF!"); 
      return; 
    }
    setError("");

    // Make sure latest state is synced
    updateWorkspace({
      cvText: localInputs.cvText,
      cvFileName: localInputs.cvFile ? localInputs.cvFile.name : cvFileName,
      jdText: localInputs.jdText || "",
      layoutData: localInputs.layoutData,
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
