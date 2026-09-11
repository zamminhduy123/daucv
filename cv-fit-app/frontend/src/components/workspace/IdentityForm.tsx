"use client";

import { Mail, Phone, MapPin, Globe, User, Briefcase, EyeOff } from "lucide-react";
import type { CVIdentity } from "@/types";
import { identityContactFields } from "@/lib/cv-edit-utils";
import PrivacyToggle from "./PrivacyToggle";

interface IdentityFormProps {
  identity: CVIdentity;
  onChange: (patch: Partial<CVIdentity>) => void;
  onHiddenChange: (hiddenFields: string[]) => void;
}

function FieldItem({
  icon: Icon,
  label,
  value,
  onChange,
  hidden,
  onToggleHidden,
  placeholder,
  inputType = "text",
  className = "",
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  onChange: (v: string) => void;
  hidden: boolean;
  onToggleHidden: () => void;
  placeholder?: string;
  inputType?: string;
  className?: string;
}) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-700">{label}</label>
        <PrivacyToggle hidden={hidden} onToggle={onToggleHidden} label={label} />
      </div>
      <div
        className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 transition-all ${
          hidden
            ? "border-amber-200 bg-amber-50/40"
            : "border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus-within:bg-white focus-within:border-[#2D7A58] focus-within:ring-2 focus-within:ring-[#2D7A58]/10"
        }`}
      >
        <Icon size={16} className={`shrink-0 ${hidden ? "text-amber-500" : "text-gray-400"}`} />
        <input
          type={inputType}
          value={value}
          placeholder={placeholder || `Chưa có ${label.toLowerCase()}`}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 min-w-0 border-0 bg-transparent text-sm text-slate-800 placeholder:text-gray-400 focus:outline-none p-0"
        />
      </div>
    </div>
  );
}

export default function IdentityForm({ identity, onChange, onHiddenChange }: IdentityFormProps) {
  const fields = identityContactFields(identity);
  const hiddenSet = new Set(identity.hidden_fields ?? []);

  const setField = (key: keyof typeof fields, value: string | string[] | null) => {
    const patch: Partial<CVIdentity> = { [key]: value } as Partial<CVIdentity>;
    onChange(patch);
  };

  const toggleHidden = (key: string) => {
    const next = identity.hidden_fields ?? [];
    const exists = next.includes(key);
    const updated = exists ? next.filter((k) => k !== key) : [...next, key];
    onHiddenChange(updated);
  };

  const links = fields.links;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FieldItem
          icon={User}
          label="Họ và tên"
          value={fields.full_name}
          onChange={(v) => setField("full_name", v)}
          hidden={hiddenSet.has("full_name")}
          onToggleHidden={() => toggleHidden("full_name")}
          placeholder="Nhập họ và tên"
        />
        <FieldItem
          icon={Briefcase}
          label="Chức danh"
          value={fields.headline}
          onChange={(v) => setField("headline", v)}
          hidden={hiddenSet.has("headline")}
          onToggleHidden={() => toggleHidden("headline")}
          placeholder="Ví dụ: AI Engineer / ML Engineer"
        />
        <FieldItem
          icon={Mail}
          label="Email"
          value={fields.email}
          onChange={(v) => setField("email", v)}
          hidden={hiddenSet.has("email")}
          onToggleHidden={() => toggleHidden("email")}
          placeholder="email@example.com"
          inputType="email"
        />
        <FieldItem
          icon={Phone}
          label="Số điện thoại"
          value={fields.phone}
          onChange={(v) => setField("phone", v)}
          hidden={hiddenSet.has("phone")}
          onToggleHidden={() => toggleHidden("phone")}
          placeholder="+84 33-545-2060"
          inputType="tel"
        />
        <FieldItem
          icon={MapPin}
          label="Địa chỉ"
          value={fields.location}
          onChange={(v) => setField("location", v)}
          hidden={hiddenSet.has("location")}
          onToggleHidden={() => toggleHidden("location")}
          placeholder="Chưa có địa điểm"
          className="sm:col-span-2"
        />
      </div>

      {/* Links list */}
      <div className="space-y-3 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe size={15} className="text-gray-400" />
            <span className="text-xs font-semibold text-slate-700">Liên kết cá nhân (LinkedIn, GitHub, Portfolio...)</span>
          </div>
          <PrivacyToggle
            hidden={hiddenSet.has("links")}
            onToggle={() => toggleHidden("links")}
            label="liên kết"
          />
        </div>
        <div className="space-y-2 pt-1">
          {links.length === 0 ? (
            <p className="text-xs text-gray-400 italic">Chưa có liên kết nào.</p>
          ) : (
            links.map((link, index) => (
              <div key={index} className="flex items-center gap-2">
                <input
                  type="text"
                  value={link}
                  placeholder="https://..."
                  onChange={(e) => {
                    const next = links.map((l, i) => (i === index ? e.target.value : l));
                    setField("links", next);
                  }}
                  className="flex-1 min-w-0 rounded-xl border border-gray-200 bg-[#FAFAFA] hover:border-gray-300 focus:bg-white px-3.5 py-2 text-xs text-slate-800 placeholder:text-gray-400 focus:border-[#2D7A58] focus:outline-none focus:ring-2 focus:ring-[#2D7A58]/10 transition-all"
                />
                <button
                  type="button"
                  onClick={() => {
                    const next = links.filter((_, i) => i !== index);
                    setField("links", next);
                  }}
                  className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-700 transition-colors"
                  aria-label="Xóa liên kết"
                >
                  ✕
                </button>
              </div>
            ))
          )}
          <button
            type="button"
            onClick={() => setField("links", [...links, ""])}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[#2D7A58] hover:underline pt-1 cursor-pointer"
          >
            + Thêm liên kết
          </button>
        </div>
      </div>

      {hiddenSet.size > 0 && (
        <p className="flex items-center gap-1.5 text-[11px] text-amber-600">
          <EyeOff size={12} />
          Đang ẩn {hiddenSet.size} trường. Các trường ẩn không xuất hiện trên bản in CV.
        </p>
      )}
    </div>
  );
}