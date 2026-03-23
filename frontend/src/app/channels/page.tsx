"use client";

import { useEffect, useState } from "react";
import { apiClient, type Channel } from "@/lib/api";
import { getTemplateName } from "@/lib/template-names";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);

  const [formData, setFormData] = useState({
    channel_id: "",
    channel_name: "",
    check_interval_minutes: 60,
    template_id: "dramatic",
    enabled: true,
  });

  useEffect(() => {
    loadChannels();
  }, []);

  const loadChannels = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getChannels();
      setChannels(response.data);
    } catch (error) {
      console.error("Failed to load channels:", error);
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    // Validate required fields
    if (!formData.channel_id.trim()) {
      alert("请输入YouTube频道ID");
      return;
    }
    if (!formData.channel_name.trim()) {
      alert("请输入频道名称");
      return;
    }

    try {
      await apiClient.createChannel(formData);
      await loadChannels();
      setShowCreate(false);
      setEditingChannel(null);
      resetForm();
    } catch (error: any) {
      console.error("Failed to create channel:", error);
      const errorMsg = error.response?.data?.detail || error.message || "创建失败";
      alert(errorMsg);
    }
  };

  const handleUpdate = async () => {
    if (!editingChannel) return;

    // Validate required fields
    if (!formData.channel_name.trim()) {
      alert("请输入频道名称");
      return;
    }

    try {
      await apiClient.updateChannel(editingChannel.id, formData);
      await loadChannels();
      setShowCreate(false);
      setEditingChannel(null);
      resetForm();
    } catch (error: any) {
      console.error("Failed to update channel:", error);
      const errorMsg = error.response?.data?.detail || error.message || "更新失败";
      alert(errorMsg);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个频道吗？")) return;
    try {
      await apiClient.deleteChannel(id);
      await loadChannels();
    } catch (error: any) {
      console.error("Failed to delete channel:", error);
      const errorMsg = error.response?.data?.detail || error.message || "删除失败";
      alert(errorMsg);
    }
  };

  const handleToggleEnabled = async (channel: Channel) => {
    try {
      await apiClient.updateChannel(channel.id, { enabled: !channel.enabled });
      await loadChannels();
    } catch (error: any) {
      console.error("Failed to toggle channel:", error);
      const errorMsg = error.response?.data?.detail || error.message || "操作失败";
      alert(errorMsg);
    }
  };

  const handleEdit = (channel: Channel) => {
    setEditingChannel(channel);
    setFormData({
      channel_id: channel.channel_id,
      channel_name: channel.channel_name,
      check_interval_minutes: channel.check_interval_minutes,
      template_id: channel.template_id,
      enabled: channel.enabled,
    });
    setShowCreate(true);
  };

  const resetForm = () => {
    setFormData({
      channel_id: "",
      channel_name: "",
      check_interval_minutes: 60,
      template_id: "dramatic",
      enabled: true,
    });
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">频道监控</h1>
          <p className="text-muted-foreground">管理 YouTube 频道监控配置</p>
        </div>
        <Button onClick={() => { resetForm(); setEditingChannel(null); setShowCreate(true); }}>+ 添加频道</Button>
      </div>

      {/* Channels Table */}
      {loading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : channels.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">还没有监控频道</p>
            <Button onClick={() => { resetForm(); setEditingChannel(null); setShowCreate(true); }}>添加第一个频道</Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-4 font-medium text-muted-foreground">频道名称</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">频道 ID</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">检查频率</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">风格模板</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">状态</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">视频数</th>
                  <th className="text-left p-4 font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((channel) => (
                  <tr key={channel.id} className="border-b border-border hover:bg-secondary/30">
                    <td className="p-4">
                      <div className="font-medium">{channel.channel_name}</div>
                    </td>
                    <td className="p-4">
                      <code className="text-sm text-muted-foreground">{channel.channel_id}</code>
                    </td>
                    <td className="p-4">
                      {channel.check_interval_minutes} 分钟
                    </td>
                    <td className="p-4">
                      <Badge variant="outline">{channel.template_id}</Badge>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => handleToggleEnabled(channel)}
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          channel.enabled
                            ? "bg-success/10 text-success"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {channel.enabled ? "已启用" : "已停用"}
                      </button>
                    </td>
                    <td className="p-4">{channel.video_count}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleEdit(channel)}>
                          编辑
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(channel.id)}>
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md bg-background shadow-xl">
            <CardHeader>
              <CardTitle>{editingChannel ? "编辑频道" : "添加频道"}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">YouTube 频道 ID</label>
                  <Input
                    value={formData.channel_id}
                    onChange={(e) => setFormData({ ...formData, channel_id: e.target.value })}
                    disabled={!!editingChannel}
                    placeholder="UCxxxxxxxxxxxxxxxxxx"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">频道名称</label>
                  <Input
                    value={formData.channel_name}
                    onChange={(e) => setFormData({ ...formData, channel_name: e.target.value })}
                    placeholder="My Channel"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">检查频率（分钟）</label>
                  <Input
                    type="number"
                    value={formData.check_interval_minutes}
                    onChange={(e) => setFormData({ ...formData, check_interval_minutes: parseInt(e.target.value) })}
                    min={5}
                    max={10080}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">使用模板</label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={formData.template_id}
                    onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
                  >
                    <option value="dramatic">{getTemplateName("dramatic")}</option>
                    <option value="humorous">{getTemplateName("humorous")}</option>
                    <option value="educational">{getTemplateName("educational")}</option>
                    <option value="chinese-documentary">{getTemplateName("chinese-documentary")}</option>
                    <option value="chinese-fun">{getTemplateName("chinese-fun")}</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2 justify-end mt-6">
                <Button variant="outline" onClick={() => { setShowCreate(false); setEditingChannel(null); }}>
                  取消
                </Button>
                <Button onClick={editingChannel ? handleUpdate : handleCreate}>
                  {editingChannel ? "更新" : "添加"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
