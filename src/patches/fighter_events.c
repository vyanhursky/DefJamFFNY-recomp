/* Native-clock timelines compiled from complete verified payload references.
 * Native loaders own their parsed tables; these files and claims stay immutable
 * for the process generation. No tag opcode or camera XML is a pack input. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_config.h"
#include "fighter_events.h"
#include "fighter_runtime.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>

#define EVENT_ROWS 65535u
static char s_names[EVENT_ROWS][8],s_tags[2048],s_cameras[2048];
static uint8_t s_flags[EVENT_ROWS];
static uint32_t s_count;
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static FILE *open_file(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];
    if (!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048)) return NULL;
    return _wfopen(wide,L"rb");
#else
    return fopen(path,"rb");
#endif
}
static int file_size(const char *path,uint32_t expected) {
    FILE *file=open_file(path);if (!file) return 0;
    int ok=!fseek(file,0,SEEK_END);long size=ok?ftell(file):-1;
    ok=ok && size>0 && (uint64_t)size<=(64ull<<20) && (uint64_t)size==expected;
    if (fclose(file)) ok=0;
    return ok;
}
int defjam_fighter_events_start(void) {
    const char *tags=defjam_fighter_env("RECOMP_FIGHTER_TAGS"),*cameras=defjam_fighter_env("RECOMP_FIGHTER_CAMERAS");
    const char *tag_hash=defjam_fighter_env("RECOMP_FIGHTER_TAGS_SHA256"),*camera_hash=defjam_fighter_env("RECOMP_FIGHTER_CAMERAS_SHA256");
    const char *binding=defjam_fighter_env("RECOMP_FIGHTER_TIMELINE_BINDINGS");
    if ((!tags || !*tags) && (!cameras || !*cameras))
        return (!binding || !*binding) && (!tag_hash || !*tag_hash) && (!camera_hash || !*camera_hash);
    if (s_count || !defjam_fighter_research_active() || !tags || !*tags || !cameras || !*cameras
        || !binding || !*binding || strlen(tags)>=sizeof s_tags || strlen(cameras)>=sizeof s_cameras
        || strlen(binding)>=2048 || !defjam_fighter_file_matches(tags,tag_hash) || !defjam_fighter_file_matches(cameras,camera_hash)) return 0;
    FILE *file=open_file(binding);if (!file) return 0;
    size_t limit=96u+12u*EVENT_ROWS;
    uint8_t *table=(uint8_t *)malloc(limit+1);if (!table) { fclose(file);return 0; }
    size_t bytes=fread(table,1,limit+1,file);
    int valid=!ferror(file) && bytes>=96 && bytes<=limit;
    if (fclose(file)) valid=0;
    uint32_t count=valid?word(table+8):0;
    if (valid) {
        char first[65],second[65];hex(table+32,first);hex(table+64,second);
        valid=!memcmp(table,"FTE1",4) && word(table+4)==1 && count && count<=EVENT_ROWS
            && bytes==96u+12u*count && word(table+12) && word(table+16) && !word(table+28)
            && !strcmp(first,tag_hash) && !strcmp(second,camera_hash)
            && file_size(tags,word(table+20)) && file_size(cameras,word(table+24));
    }
    for (uint32_t i=0;valid && i<count;++i) {
        const uint8_t *row=table+96+12*i;
        unsigned length=0;while (length<8 && row[length]) ++length;
        if (!length || word(row+8)>3 || (i && memcmp(row-12,row,8)>=0)) { valid=0;break; }
        for (unsigned c=0;c<8;++c) {
            unsigned b=row[c];
            if (c>=length ? b!=0 : !((b>='A' && b<='Z') || (b>='a' && b<='z') || (b>='0' && b<='9') || b=='_')) valid=0;
        }
        if (valid) { memcpy(s_names[i],row,8);s_flags[i]=(uint8_t)word(row+8); }
    }
    if (valid) {
        s_count=count;strcpy(s_tags,tags);strcpy(s_cameras,cameras);
        fprintf(stderr,"[FIGHTERS] validated %u owned camera/tag timeline identities\n",count);
    }
    free(table);return valid;
}
int defjam_fighter_events_has(const char *name,unsigned flags) {
    if (!s_count || !name || !*name || flags>3 || strlen(name)>8) return 0;
    char key[8]={0};memcpy(key,name,strlen(name));
    uint32_t low=0,high=s_count;
    while (low<high) {
        uint32_t middle=low+(high-low)/2;int cmp=memcmp(key,s_names[middle],8);
        if (!cmp) return (s_flags[middle]&flags)==flags;
        if (cmp<0) high=middle;else low=middle+1;
    }
    return 0;
}
const char *defjam_fighter_events_tags_path(void) { return s_tags; }
const char *defjam_fighter_events_cameras_path(void) { return s_cameras; }
