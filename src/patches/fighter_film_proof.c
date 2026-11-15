/* Compiler-owned full cinematic seals and actual actor joins. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "fighter_config.h"
#include "fighter_film_proof.h"
#include "recomp/gen/recomp_types.h"
#include "fighter_cpu_pool.h"
#include "fighter_graph_proof.h"
#include "fighter_events.h"
#include "fighter_runtime.h"
#include "fighter_cinematic.h"
#include "hooks/mod_sha256.h"
#include <stdlib.h>
#define FILM_LIMIT 8192u
static struct {const uint8_t *record;uint32_t bank;} s_films[FILM_LIMIT];
static uint8_t *s_data;
static unsigned s_count,s_logs;
static struct {unsigned proof;uint32_t bank;} s_instances[512];
static unsigned s_instances_count;
static size_t token_width(const char *name) {return name[0]=='B'?6u:7u;}
static uint32_t word(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int equal_fold(const char *a,const char *b,size_t length) {
    for (size_t i=0;i<length;++i) {
        unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];
        if (x>='A'&&x<='Z') x+=32;
        if (y>='A'&&y<='Z') y+=32;
        if (x!=y) return 0;
    }
    return 1;
}
static FILE *open_file(const char *path) {
#if defined(_WIN32)
    wchar_t wide[2048];if (!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path,-1,wide,2048)) return NULL;
    return _wfopen(wide,L"rb");
#else
    return fopen(path,"rb");
#endif
}
int defjam_fighter_film_start(void) {
    const char *path=defjam_fighter_env("RECOMP_FIGHTER_FILM_PROOFS");if (!path || !*path) return defjam_fighter_cinematic_proofs();
    const char *archive=defjam_fighter_env("RECOMP_FIGHTER_CINEMATIC_BANKS"),*hash=defjam_fighter_env("RECOMP_FIGHTER_CINEMATIC_BANKS_SHA256");
    if (s_count || strlen(path)>=2048 || !archive || !hash || !defjam_fighter_file_matches(archive,hash)) return 0;
    FILE *file=open_file(path);if (!file) return 0;
    uint8_t *data=(uint8_t *)malloc((64u<<20)+1);if (!data) {fclose(file);return 0;}
    size_t bytes=fread(data,1,(64u<<20)+1,file);int valid=!ferror(file) && bytes>=52 && bytes<=(64u<<20);
    if (fclose(file)) valid=0;
    uint32_t count=valid?word(data+8):0;char digest[65];
    if (valid) {hex(data+20,digest);valid=!memcmp(data,"FCP1",4) && word(data+4)==1 && count && count<=FILM_LIMIT
        && !word(data+16) && !strcmp(digest,hash);}
    if (valid) {
        FILE *f=open_file(archive);if (!f) valid=0;
        else {long size=fseek(f,0,SEEK_END)?-1:ftell(f);if (size<0 || (uint64_t)size!=word(data+12)) valid=0;if (fclose(f)) valid=0;}
    }
    size_t at=52;const uint8_t *previous=NULL;
    for (unsigned i=0;valid && i<count;++i) {
        if (bytes-at<128) {valid=0;break;}const uint8_t *p=data+at;
        unsigned length=0;while (length<32 && p[length]) ++length;
        uint32_t size=word(p+32),root=word(p+36),relocs=word(p+40),bones=word(p+44),role=word(p+56),tags=word(p+60);
        size_t record_bytes=128u+8u*relocs;
        if (!length || length>=32 || (previous && memcmp(previous,p,32)>=0) || record_bytes>bytes-at
            || size<24 || size>(32u<<20) || root>size-24 || !relocs || relocs>65536 || !bones || bones>256
            || word(p+48)>32 || word(p+52)>32 || (!word(p+48)!=!word(p+52)) || role<1 || role>4 || tags>1) {valid=0;break;}
        for (unsigned c=0;c<32;++c) if (c>=length ? p[c]!=0 : !((p[c]>='A'&&p[c]<='Z')||(p[c]>='a'&&p[c]<='z')||(p[c]>='0'&&p[c]<='9')||p[c]=='_'||p[c]=='.')) valid=0;
        size_t stem=token_width((const char *)p);
        if (p[0]!='B' && !(p[0]=='F' && (p[1]=='I'||p[1]=='V'))) valid=0;
        for (size_t c=p[0]=='B'?1u:2u;c<stem;++c) if (p[c]<'0'||p[c]>'9') valid=0;
        const char *suffix=(const char *)p+stem;
        if (role==1?strcmp(suffix,".o"):role==2?strcmp(suffix,"_f.o"):role==3?strcmp(suffix,"_h.o"):
            (strcmp(suffix,"_EYE.o") && strcmp(suffix,"_TARGET.o") && strcmp(suffix,"1_EYE.o")
             && strcmp(suffix,"1_TARGET.o") && strcmp(suffix,"2_EYE.o") && strcmp(suffix,"2_TARGET.o"))) valid=0;
        uint32_t end=0;
        for (unsigned j=0;valid && j<relocs;++j) {
            uint32_t field=word(p+128+8*j),target=word(p+132+8*j);
            if (field<end || (field&3) || field>size-4 || target>=size) valid=0;
            end=field+4;
        }
        s_films[i].record=p;previous=p;at+=record_bytes;
    }
    if (!valid || at!=bytes) {memset(s_films,0,sizeof s_films);free(data);return 0;}
    s_data=data;s_count=count;
    if (!defjam_fighter_cinematic_proofs()) {s_data=NULL;s_count=0;memset(s_films,0,sizeof s_films);free(data);return 0;}
    fprintf(stderr,"[FIGHTERS] validated %u full cinematic member proofs\n",count);return 1;
}
unsigned defjam_fighter_film_file(const char *path) {
    if (!s_count || !path) return 0;
    const char *prefix="assets/v2ta.viv|";size_t n=strlen(prefix);
    for (size_t i=0;i<n;++i) {char c=path[i];if (c=='\\') c='/';if (c>='A'&&c<='Z') c+=32;if (c!=prefix[i]) return 0;}
    path+=n;const char *separator=strchr(path,'|');if (separator && separator-path>16) return 0;
    for (unsigned i=0;i<s_count;++i) {
        const char *name=(const char *)s_films[i].record;size_t stem=token_width(name);
        size_t bundle_length=separator?(size_t)(separator-path):strlen(path);
        if (bundle_length!=stem+4 || !equal_fold(path,name,stem) || !equal_fold(path+stem,".viv",4)) continue;
        if (!separator) return i+1; /* Nested .o members borrow this whole BIG allocation. */
        if (strlen(separator+1)==strlen(name) && equal_fold(separator+1,name,strlen(name))) return i+1;
    }
    return 0;
}
static int seal(unsigned owner,uint32_t bank) {
    const uint8_t *p=s_films[owner-1].record;uint32_t size=word(p+32),root=word(p+36),relocs=word(p+40);
    if (bank<root) return 0;
    uint32_t base=bank-root;
    if (!defjam_fighter_cpu_range(base,size)) return 0;
    Sha sha;sha_init(&sha);uint32_t end=0;
    for (unsigned j=0;j<relocs;++j) {
        uint32_t field=word(p+128+8*j),target=word(p+132+8*j);
        if (MEM32(base+field)!=base+target) return 0;
        sha_update(&sha,(const void *)XBOX_PTR(base+end),field-end);sha_update(&sha,p+132+8*j,4);end=field+4;
    }
    sha_update(&sha,(const void *)XBOX_PTR(base+end),size-end);uint8_t digest[32];sha_final(&sha,digest);
    if (memcmp(digest,p+96,32)) return 0;
    s_films[owner-1].bank=bank;
    unsigned instance=0;
    for (;instance<s_instances_count;++instance) if (s_instances[instance].bank==bank) break;
    if (instance==s_instances_count) {if (s_instances_count>=512) return 0;++s_instances_count;}
    s_instances[instance].proof=owner;s_instances[instance].bank=bank;
    if (++s_logs<=256) fprintf(stderr,"[FIGHTERS] cinematic sealed before constructor member=%s bank=%08X bytes=%u\n",p,bank,size);
    return 1;
}
int defjam_fighter_film_preconstruct(uint32_t bank) {
    unsigned owner=defjam_fighter_cpu_film(bank);if (!owner) return 1;
    if (owner>s_count) return 0;
    const char *name=(const char *)s_films[owner-1].record;size_t stem=token_width(name);
    for (unsigned i=0;i<s_count;++i)
        if (!strncmp((const char *)s_films[i].record,name,stem) && token_width((const char *)s_films[i].record)==stem
            && seal(i+1,bank)) return 1;
    return 0;
}
static unsigned find(const char *name,const char *suffix) {
    char member[32];if (snprintf(member,sizeof member,"%s%s",name,suffix)<0) return 0;
    for (unsigned i=0;i<s_count;++i) if (!strcmp(member,(const char *)s_films[i].record)) return i+1;
    return 0;
}
int defjam_fighter_film_known(const char *name) {return find(name,".o")!=0;}
int defjam_fighter_film_complete(const char *name,int intro) {
    if (!name || !find(name,".o") || !find(name,"_f.o") || !find(name,"_h.o")) return 0;
    if (intro) return find(name,"1_EYE.o") && find(name,"1_TARGET.o") && find(name,"2_EYE.o") && find(name,"2_TARGET.o");
    return find(name,"_EYE.o") && find(name,"_TARGET.o");
}
static int sealed(unsigned proof,uint32_t bank) {
    if (!bank || !proof) return 0;
    for (unsigned i=0;i<s_instances_count;++i) if (s_instances[i].proof==proof && s_instances[i].bank==bank) return 1;
    return 0;
}
int defjam_fighter_film_bind(const char *name,uint32_t entry,uint32_t visual,uint32_t descriptor) {
    unsigned id=find(name,".o");if (!id) return 1;
    const uint8_t *p=s_films[id-1].record;
    unsigned face=find(name,"_f.o"),hands=find(name,"_h.o");
    if (!sealed(id,MEM32(entry+0x24)) || !sealed(face,MEM32(entry+0x30))
        || !sealed(hands,MEM32(entry+0x3C)) || !defjam_fighter_events_has(name,word(p+60))) return 0;
    int absolute=defjam_fighter_cinematic_absolute(descriptor);
    if (absolute && (!(MEM8(descriptor)&8) || strcmp((const char *)XBOX_PTR(descriptor+0x1D),name))) return 0;
    if (!(MEM8(descriptor)&8) || absolute) {
        uint32_t table=MEM32(descriptor+0x88);unsigned category=MEM32(descriptor+0xA4),selector=MEM32(descriptor+0x98);
        if (!table || MEM32(descriptor+0x8C)!=2 || (category==0 && selector>1)
            || strcmp((const char *)XBOX_PTR(table),"CAM_TARGET") || strcmp((const char *)XBOX_PTR(table+0x2C),"CAM_EYE")) return 0;
        const char *eye=category==0?(selector?"2_EYE.o":"1_EYE.o"):"_EYE.o";
        const char *target=category==0?(selector?"2_TARGET.o":"1_TARGET.o"):"_TARGET.o";
        if (!sealed(find(name,target),MEM32(table+0x24)) || !sealed(find(name,eye),MEM32(table+0x50))
            || !MEM32(descriptor+0x13C)) return 0;
    } else if (MEM32(descriptor+0xA4)!=2 || MEM32(descriptor+0xD4)!=3) return 0;
    uint32_t hand_need[2]={word(p+48),word(p+52)};
    return defjam_fighter_graph_visual(visual,word(p+44),p+64,1,NULL,hand_need);
}
void defjam_fighter_film_release(void) {for (unsigned i=0;i<s_count;++i) s_films[i].bank=0;s_logs=s_instances_count=0;}
