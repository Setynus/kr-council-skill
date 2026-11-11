# 릴리스 점검 목록

새 버전을 태그하고 릴리스하기 직전에 한다(저장소는 처음부터 공개다).

1. **이력 재검사**: 아래 두 명령의 결과가 모두 비어 있어야 한다. 검색어를 대괄호로 쪼개 이 문서 자신이 걸리지 않게 했다.
   - `git log --all -p | grep -n -E '@g[m]ail|g[h]p_|s[k]-[A-Za-z0-9]{20}|C:.Use[r]s|Claude[C]ode'`
   - `git log --all --format='%ae %ce' | sort -u` 에는 noreply 주소 하나만 나와야 한다.
2. **테스트와 패키지**: `python -m unittest discover tests`가 통과하는지, `python tools/package_skill.py`로 만든 zip을 풀어 `render_report.py`가 돌아가는지 확인한다.
3. **버전 맞추기**: `kr-council-skill/SKILL.md`의 `metadata.version`과 태그(`vX.Y.Z`)가 같아야 한다.
4. **GitHub 비밀값 검사**: 저장소 Settings → Code security에서 secret scanning과 push protection을 켠다.
5. **개인 데이터**: `comparison/` 질문과 결과는 가상의 사례다. 실제 사용자의 질문이나 보고서가 섞이지 않았는지 훑는다(`council-reports/`는 `.gitignore`).
6. **캐릭터 호칭**: 위원 호칭이 상표인 스머프 캐릭터 이름이다. 공개하면 권리자와 무관함을 밝힌 `NOTICE.md` 문구가 있는지 확인하고, 부담스러우면 호칭을 일반 이름으로 바꾼다(`kr-council-skill/SKILL.md`의 위원 이름 표와 `references/advisors.md`, 렌더러 템플릿의 위원장 제목만 바꾸면 된다).
7. **릴리스**: `git tag -a vX.Y.Z -m "..."`, `git push origin vX.Y.Z`, `gh release create vX.Y.Z dist/kr-council-skill.zip --notes-file <노트>`
