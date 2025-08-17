import cv2, numpy as np
def draw_overlay(frame, result):
    if result is None: return frame
    t = result.get("type")
    if t=="apriltag":
        for it in result.get("items", []):
            pts = np.array(it.get("corners", []), int)
            if pts.shape==(4,2):
                for i in range(4):
                    cv2.line(frame, tuple(pts[i]), tuple(pts[(i+1)%4]), (0,255,0), 1)
                cv2.putText(frame, f"ID {it.get('id','?')}", tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    elif t=="object":
        for it in result.get("items", []):
            x1,y1,x2,y2 = it.get("box",[0,0,0,0])
            cv2.rectangle(frame,(x1,y1),(x2,y2),(255,0,0),1)
            cv2.putText(frame, f"{it.get('label','obj')} {it.get('conf',0):.2f}", (x1,max(0,y1-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0),1)
    elif t in ("color","block"):
        for it in result.get("items", []):
            x1,y1,x2,y2 = it.get("box",[0,0,0,0])
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),1)
            label = it.get("color","block") if t=="color" else it.get("label","block")
            cv2.putText(frame, label, (x1,max(0,y1-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255),1)
    return frame
