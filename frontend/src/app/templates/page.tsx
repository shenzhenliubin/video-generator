"use client";

import { useEffect, useState } from "react";
import { apiClient, type Template } from "@/lib/api";
import { getTemplateName, getCategoryName } from "@/lib/template-names";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);

  const [formData, setFormData] = useState({
    id: "",
    name: "",
    category: "dramatic",
    description: "",
    llm_provider: "siliconflow",
    image_provider: "siliconflow",
    tts_provider: "siliconflow",
    scene_duration: 5,
    image_style_prompt: "",
    voice_id: "",
    system_prompt: "",
    temperature: 0.7,
    max_tokens: 1000,
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getTemplates();
      setTemplates(response.data);
    } catch (error) {
      console.error("Failed to load templates:", error);
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    // Client-side validation: check if ID already exists
    const existingTemplate = templates.find(t => t.id === formData.id);
    if (existingTemplate) {
      alert(`模板ID "${formData.id}" 已存在，请使用不同的ID`);
      return;
    }

    // Validate required fields
    if (!formData.id.trim()) {
      alert("请输入模板ID");
      return;
    }
    if (!formData.name.trim()) {
      alert("请输入模板名称");
      return;
    }

    try {
      await apiClient.createTemplate(formData);
      await loadTemplates();
      setShowCreate(false);
      setEditingTemplate(null);
      resetForm();
    } catch (error: any) {
      console.error("Failed to create template:", error);
      const errorMsg = error.response?.data?.detail || error.message || "创建失败";
      alert(errorMsg);
    }
  };

  const handleUpdate = async () => {
    if (!editingTemplate) return;

    // Validate required fields
    if (!formData.name.trim()) {
      alert("请输入模板名称");
      return;
    }

    try {
      await apiClient.updateTemplate(editingTemplate.id, formData);
      await loadTemplates();
      setShowCreate(false);
      setEditingTemplate(null);
      resetForm();
    } catch (error: any) {
      console.error("Failed to update template:", error);
      const errorMsg = error.response?.data?.detail || error.message || "更新失败";
      alert(errorMsg);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个风格模板吗？")) return;
    try {
      await apiClient.deleteTemplate(id);
      await loadTemplates();
    } catch (error: any) {
      console.error("Failed to delete template:", error);
      const errorMsg = error.response?.data?.detail || error.message || "删除失败";
      alert(errorMsg);
    }
  };

  const handleEdit = (template: Template) => {
    setEditingTemplate(template);
    setFormData({
      id: template.id,
      name: template.name,
      category: template.category,
      description: template.description,
      llm_provider: template.llm_provider,
      image_provider: template.image_provider,
      tts_provider: template.tts_provider,
      scene_duration: template.scene_duration,
      image_style_prompt: template.image_style_prompt,
      voice_id: template.voice_id || "",
      system_prompt: template.system_prompt,
      temperature: template.temperature,
      max_tokens: template.max_tokens,
    });
    setShowCreate(true);
  };

  const resetForm = () => {
    setFormData({
      id: "",
      name: "",
      category: "dramatic",
      description: "",
      llm_provider: "siliconflow",
      image_provider: "siliconflow",
      tts_provider: "siliconflow",
      scene_duration: 5,
      image_style_prompt: "",
      voice_id: "",
      system_prompt: "",
      temperature: 0.7,
      max_tokens: 1000,
    });
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">风格模板</h1>
          <p className="text-muted-foreground">管理和配置视频生成风格</p>
        </div>
        <Button onClick={() => { resetForm(); setEditingTemplate(null); setShowCreate(true); }}>+ 新建模板</Button>
      </div>

      {/* Template List */}
      {loading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">还没有风格模板</p>
            <Button onClick={() => { resetForm(); setEditingTemplate(null); setShowCreate(true); }}>创建第一个模板</Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-4 font-medium text-muted-foreground">ID</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">名称</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">类别</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">描述</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">LLM</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">图像</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">语音</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">时长</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => (
                  <tr key={template.id} className="border-b border-border hover:bg-secondary/30">
                    <td className="p-4">
                      <code className="text-sm text-muted-foreground">{template.id}</code>
                    </td>
                    <td className="p-4">
                      <div className="font-medium">{getTemplateName(template.id, template.name)}</div>
                    </td>
                    <td className="p-4">
                      <Badge variant="outline">{getCategoryName(template.category)}</Badge>
                    </td>
                    <td className="p-4 text-sm text-muted-foreground max-w-xs truncate">
                      {template.description}
                    </td>
                    <td className="p-4 text-sm">{template.llm_provider}</td>
                    <td className="p-4 text-sm">{template.image_provider}</td>
                    <td className="p-4 text-sm">{template.tts_provider}</td>
                    <td className="p-4 text-sm">{template.scene_duration}s</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleEdit(template)}>
                          编辑
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(template.id)}>
                          删除
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-4xl bg-background shadow-xl max-h-full overflow-hidden flex flex-col">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">
                {editingTemplate ? "编辑模板" : "新建模板"}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              <div className="grid grid-cols-4 gap-3">
                {/* Basic Info */}
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">ID</label>
                  <Input
                    value={formData.id}
                    onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                    disabled={!!editingTemplate}
                    placeholder="dramatic"
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">名称</label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="戏剧性"
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">类别</label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    <option value="dramatic">戏剧性</option>
                    <option value="humorous">幽默风趣</option>
                    <option value="educational">教育科普</option>
                    <option value="cinematic">电影感</option>
                    <option value="documentary">纪录片</option>
                  </select>
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">场景时长(秒)</label>
                  <Input
                    type="number"
                    value={formData.scene_duration}
                    onChange={(e) => setFormData({ ...formData, scene_duration: parseInt(e.target.value) || 5 })}
                    min={1}
                    max={30}
                    className="h-9 text-sm"
                  />
                </div>

                {/* Description */}
                <div className="col-span-4">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">描述</label>
                  <Input
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="风格描述"
                    className="h-9 text-sm"
                  />
                </div>

                {/* Image Style Prompt */}
                <div className="col-span-2">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">图像风格提示词</label>
                  <textarea
                    className="flex h-16 w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none"
                    value={formData.image_style_prompt}
                    onChange={(e) => setFormData({ ...formData, image_style_prompt: e.target.value })}
                    placeholder="cinematic, dramatic lighting, high contrast"
                  />
                </div>

                {/* System Prompt */}
                <div className="col-span-2">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">系统提示词</label>
                  <textarea
                    className="flex h-16 w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none"
                    value={formData.system_prompt}
                    onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                    placeholder="You are a dramatic storyteller..."
                  />
                </div>

                {/* Providers */}
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">LLM 提供商</label>
                  <Input
                    value={formData.llm_provider}
                    onChange={(e) => setFormData({ ...formData, llm_provider: e.target.value })}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">图像提供商</label>
                  <Input
                    value={formData.image_provider}
                    onChange={(e) => setFormData({ ...formData, image_provider: e.target.value })}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">TTS 提供商</label>
                  <Input
                    value={formData.tts_provider}
                    onChange={(e) => setFormData({ ...formData, tts_provider: e.target.value })}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">语音 ID</label>
                  <Input
                    value={formData.voice_id}
                    onChange={(e) => setFormData({ ...formData, voice_id: e.target.value })}
                    placeholder="charles"
                    className="h-9 text-sm"
                  />
                </div>

                {/* Advanced Settings */}
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">温度</label>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    max={2}
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) || 0.7 })}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">最大 Tokens</label>
                  <Input
                    type="number"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) || 1000 })}
                    className="h-9 text-sm"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end mt-4 pt-4 border-t border-border">
                <Button variant="outline" onClick={() => { setShowCreate(false); setEditingTemplate(null); }}>
                  取消
                </Button>
                <Button onClick={editingTemplate ? handleUpdate : handleCreate}>
                  {editingTemplate ? "更新" : "创建"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
