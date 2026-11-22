// Photo controls and guides are host overlays, outside the captured game target.
#include "imgui.h"
#include "patches/photo_mode.h"
extern "C" {
#include "patches/widescreen.h"
}
#include <cstdio>

extern "C" void photo_mode_ui(void)
{
    PhotoModeStatus s{};
    photo_mode_status(&s);
    if (!s.active) return;
    ImGuiIO &io = ImGui::GetIO();
    ImDrawList *guides = ImGui::GetBackgroundDrawList();
    float aspect = ws_aspect();
    if (aspect <= 0) aspect = 4.0f / 3.0f;
    float width = io.DisplaySize.x, height = io.DisplaySize.y;
    if (width / height > aspect) width = height * aspect;
    else height = width / aspect;
    ImVec2 lo((io.DisplaySize.x-width)*0.5f, (io.DisplaySize.y-height)*0.5f);
    ImVec2 hi(lo.x+width, lo.y+height);
    if (s.thirds) {
        for (int i=1; i<3; ++i) {
            float x=lo.x+width*i/3, y=lo.y+height*i/3;
            guides->AddLine(ImVec2(x,lo.y),ImVec2(x,hi.y),IM_COL32(255,255,255,135));
            guides->AddLine(ImVec2(lo.x,y),ImVec2(hi.x,y),IM_COL32(255,255,255,135));
        }
    }
    if (s.centre) {
        ImVec2 c(lo.x+width*0.5f,lo.y+height*0.5f);
        guides->AddLine(ImVec2(c.x-10,c.y),ImVec2(c.x+10,c.y),IM_COL32(255,255,255,210));
        guides->AddLine(ImVec2(c.x,c.y-10),ImVec2(c.x,c.y+10),IM_COL32(255,255,255,210));
    }
    if (!s.panel) return;
    const float margin=ImGui::GetFontSize();
    ImGui::SetNextWindowPos(ImVec2(lo.x+margin,hi.y-margin),ImGuiCond_Always,ImVec2(0,1));
    ImGui::SetNextWindowSizeConstraints(ImVec2(350,0),ImVec2(width-margin*2,height-margin*2));
    ImGui::SetNextWindowBgAlpha(0.87f);
    const ImGuiWindowFlags flags=ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_AlwaysAutoResize |
        ImGuiWindowFlags_NoInputs | ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoFocusOnAppearing;
    ImGui::Begin("Photo Mode##photo",nullptr,flags);
    ImGui::TextColored(ImVec4(1.0f,0.78f,0.32f,1),"PHOTO MODE");
    ImGui::TextDisabled("Fight frozen");
    if (s.settings) {
        static const char *labels[]={"Field of view","Roll","Travel speed","Look speed","Invert look Y",
            "Game HUD","Rule of thirds","Centre guide","Reset camera"};
        static const char *speeds[]={"Slow","Normal","Fast","Very fast"};
        char values[9][48]{};
        std::snprintf(values[0],sizeof(values[0]),"%.0f deg",s.fov);
        std::snprintf(values[1],sizeof(values[1]),"%.0f deg",s.roll);
        std::snprintf(values[2],sizeof(values[2]),"%s",speeds[s.speed%4]);
        std::snprintf(values[3],sizeof(values[3]),"%.2fx",s.look_speed);
        std::snprintf(values[4],sizeof(values[4]),"%s",s.invert_y ? "On" : "Off");
        std::snprintf(values[5],sizeof(values[5]),"%s",s.hud_hidden ? "Hidden" : "Shown");
        std::snprintf(values[6],sizeof(values[6]),"%s",s.thirds ? "On" : "Off");
        std::snprintf(values[7],sizeof(values[7]),"%s",s.centre ? "On" : "Off");
        std::snprintf(values[8],sizeof(values[8]),"A / Cross");
        ImGui::Separator();
        if (ImGui::BeginTable("photo settings",2,ImGuiTableFlags_SizingStretchProp)) {
            ImGui::TableSetupColumn("Setting",ImGuiTableColumnFlags_WidthStretch,1.5f);
            ImGui::TableSetupColumn("Value",ImGuiTableColumnFlags_WidthStretch,1.0f);
            for (int i=0;i<9;++i) {
                ImGui::TableNextRow();
                if (i==s.row) ImGui::TableSetBgColor(ImGuiTableBgTarget_RowBg0,IM_COL32(145,105,30,160));
                ImGui::TableNextColumn(); ImGui::TextUnformatted(labels[i]);
                ImGui::TableNextColumn(); ImGui::TextUnformatted(values[i]);
            }
            ImGui::EndTable();
        }
        ImGui::Separator();
        ImGui::TextUnformatted("D-pad: select / change    B / Circle: back");
    } else {
        ImGui::TextUnformatted("Left stick: move    Right stick: look");
        ImGui::TextUnformatted("LT / RT: down / up    LB / RB: zoom");
        ImGui::Separator();
        ImGui::TextUnformatted("A / Cross: photo    Y / Triangle: settings");
        ImGui::TextUnformatted("X / Square: hide controls    B / Circle: exit");
    }
    if (s.message[0]) {
        ImGui::Separator();
        ImGui::PushTextWrapPos(ImGui::GetCursorPosX()+ImGui::GetFontSize()*30);
        ImGui::TextUnformatted(s.message);
        ImGui::PopTextWrapPos();
    }
    ImGui::End();
}
