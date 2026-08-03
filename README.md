# שער להרפתקה — אתר סטטי

אתר סטטי טהור (HTML, CSS, JS, JSON) — בלי שרת, בלי מסד נתונים, בלי פורטל ניהול.
מוכן להעלאה ישירה ל-GitHub Pages, בדיוק כמו המקור. כולל את כל השיפורים: שאלון המלצה,
"מתקיים ב<חודש>" בכרטיסים, צור-קשר במייל, פוטר מעודכן, וקבצי SEO/GEO.

## מבנה
```
index.html          עמוד הבית
search.html         חיפוש
quiz.html           שאלון ההמלצה למתחילים
404.html            עמוד שגיאה
data.json           כל הנתונים (קהילה, משאבים, אזורים) — עורכים אותו כדי לעדכן תוכן
sitemap.xml · robots.txt · llms.txt · agents.json   קבצי SEO / GEO
articles/           עמודי המאמרים
static/             תמונות, search-engine.js, וקובצי ה-Markdown של המאמרים
CNAME               הדומיין (gate.roleplay.top)
.nojekyll           משבית את Jekyll כדי שקובצי ה-.md יוגשו כמו שהם
```

## העלאה ל-GitHub Pages
```
cd rpg-gate-static
git init
git add .
git commit -m "שער להרפתקה - אתר סטטי"
git branch -M main
git remote add origin https://github.com/<שם-משתמש>/<שם-ריפו>.git
git push -u origin main
```
ואז ב-GitHub: Settings → Pages → Branch: main → /(root) → Save.

### חשוב — האתר חייב לשבת בשורש הדומיין
כל הקישורים מוחלטים (כמו /search, /data.json, /static/...), ולכן האתר צריך לשבת
בשורש הדומיין. שתי דרכים תקינות:
- דומיין מותאם אישית (כמו במקור) — קובץ ה-CNAME כבר מגדיר את gate.roleplay.top.
  אם אינך רוצה את הדומיין הזה, מחק את קובץ ה-CNAME.
- ריפו בשם <שם-משתמש>.github.io — אז האתר יושב בשורש https://<שם-משתמש>.github.io/.

הערה: אם תעלה לריפו רגיל (כתובת מסוג username.github.io/repo-name/) הקישורים המוחלטים יישברו.

## איך מעדכנים תוכן?
אין יותר פורטל ניהול — עורכים ישירות את data.json:
- communityData — ארגונים, כנסים וקבוצות (עם שדה month לאירועים: 1–12, או 0 ללא).
- resourcesData — חנויות, מתחמים, סדנאות וחוגי ילדים.
- regions — אזורים ויישובים (משמש למנוע החיפוש).

שומרים, עושים commit ו-push — והאתר מתעדכן. מאמר חדש: מוסיפים קובץ HTML תחת articles/.
