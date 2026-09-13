import { IconFacebook, IconInstagram } from "./icons";
import { Card } from "./ui";
import { useLanguage } from "../i18n";

export function PlatformPreview({
  platform,
  text,
  imageUrl,
}: {
  platform: "Facebook" | "Instagram";
  text: string;
  imageUrl: string;
}) {
  const { language } = useLanguage();
  return (
    <Card className="platform-preview">
      <div className="ph-head">
        <span className="ph-avatar" aria-hidden="true">
          {platform === "Facebook" ? (
            <IconFacebook size={17} />
          ) : (
            <IconInstagram size={17} />
          )}
        </span>
        <span>
          {platform}
          <br />
          <small style={{ color: "var(--faint)", fontWeight: 500 }}>
            {language === "ar" ? "معاينة المنشور" : "Post preview"}
          </small>
        </span>
      </div>
      <img
        src={imageUrl}
        alt={language === "ar" ? "معاينة صورة المنتج" : "Product image preview"}
      />
      <p>{text}</p>
    </Card>
  );
}
