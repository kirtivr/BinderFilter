/*
{(1)%android.intent.action.BATTERY_CHANGED(255)(255)(255)(255)(16)`(255)(255)(255)(255)(255)(255)(255)(255)(254)(255)(255)(255)(160)(10)BNDL(12)(10)technology(6)Li-ion(10)icon-small(1)Q(6)(8)(1)(6)health(1)(2)(20)max_charging_current(1)(6)status(1)(5)(7)plugged(1)(2)(7)present(9)(1)(5)level(1)d(5)scale(1)d(11)temperature(1)(200)(70)voltage}
*/

// Intent.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/Intent.java
public void readFromParcel(Parcel in) {
    setAction(in.readString());
    mData = Uri.CREATOR.createFromParcel(in);
    mType = in.readString();
    mFlags = in.readInt();
    mPackage = in.readString();
    mComponent = ComponentName.readFromParcel(in);

    if (in.readInt() != 0) {
        mSourceBounds = Rect.CREATOR.createFromParcel(in);
    }

    int N = in.readInt();
    if (N > 0) {
        mCategories = new ArraySet<String>();
        int i;
        for (i=0; i<N; i++) {
            mCategories.add(in.readString().intern());
        }
    } else {
        mCategories = null;
    }

    if (in.readInt() != 0) {
        mSelector = new Intent(in);
    }

    if (in.readInt() != 0) {
        mClipData = new ClipData(in);
    }
    mContentUserHint = in.readInt();
    mExtras = in.readBundle();
}

// Uri.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// Uri.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/net/Uri.java
public Uri createFromParcel(Parcel in) {
    int type = in.readInt();
    switch (type) {
        case NULL_TYPE_ID: return null;
        case StringUri.TYPE_ID: return StringUri.readFrom(in);
        case OpaqueUri.TYPE_ID: return OpaqueUri.readFrom(in);
        case HierarchicalUri.TYPE_ID:
            return HierarchicalUri.readFrom(in);
    }

    throw new IllegalArgumentException("Unknown URI type: " + type);
}

// StringUri
static Uri readFrom(Parcel parcel) {
    return new StringUri(parcel.readString());
}

// OpaqueUri
static Uri readFrom(Parcel parcel) {
    return new OpaqueUri(
        parcel.readString(),
        Part.readFrom(parcel),
        Part.readFrom(parcel)
    );
}

// HierarchicalUri
 static Uri readFrom(Parcel parcel) {
    return new HierarchicalUri(
        parcel.readString(),
        Part.readFrom(parcel),
        PathPart.readFrom(parcel),
        Part.readFrom(parcel),
        Part.readFrom(parcel)
    );
}

//Part (same as PathPart)
 static Part readFrom(Parcel parcel) {
    int representation = parcel.readInt();
    switch (representation) {
        case Representation.BOTH:
            return from(parcel.readString(), parcel.readString());
        case Representation.ENCODED:
            return fromEncoded(parcel.readString());
        case Representation.DECODED:
            return fromDecoded(parcel.readString());
        default:
            throw new IllegalArgumentException("Unknown representation: "
                    + representation);
    }
}

from(String encoded, String decoded) {
    ...
    return new Part(encoded, decoded);
}


// ComponentName.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// ComponentName.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/ComponentName.java

public static ComponentName readFromParcel(Parcel in) {
    String pkg = in.readString();
    return pkg != null ? new ComponentName(pkg, in) : null;
}

private ComponentName(String pkg, Parcel in) {
    mPackage = pkg;
    mClass = in.readString();
}


// Rect.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// Rect.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/graphics/java/android/graphics/Rect.java
public void readFromParcel(Parcel in) {
    left = in.readInt();
    top = in.readInt();
    right = in.readInt();
    bottom = in.readInt();
}

// new Intent(in) ---------------------------------------------------------------------------------------------------

protected Intent(Parcel in) {
    readFromParcel(in);
}

// new Clipdata(in) ---------------------------------------------------------------------------------------------------
// ClipData.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/ClipData.java
ClipData(Parcel in) {
    mClipDescription = new ClipDescription(in);
    if (in.readInt() != 0) {
        mIcon = Bitmap.CREATOR.createFromParcel(in);
    } else {
        mIcon = null;
    }
    mItems = new ArrayList<Item>();
    final int N = in.readInt();
    for (int i=0; i<N; i++) {
        CharSequence text = TextUtils.CHAR_SEQUENCE_CREATOR.createFromParcel(in);
        String htmlText = in.readString();
        Intent intent = in.readInt() != 0 ? Intent.CREATOR.createFromParcel(in) : null;
        Uri uri = in.readInt() != 0 ? Uri.CREATOR.createFromParcel(in) : null;
        mItems.add(new Item(text, htmlText, intent, uri));
    }
}


// Parcel.read*() ---------------------------------------------------------------------------------------------------
// java -> http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/os/Parcel.java
// calls native method -> http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/jni/android_os_Parcel.cpp
// jni layer -> calls cpp method -> http://androidxref.com/6.0.1_r10/xref/frameworks/native/libs/binder/Parcel.cpp


// java
public final String readString() {
    return nativeReadString(mNativePtr);
}
public final int readInt() {
    return nativeReadInt(mNativePtr);
}

// jni
static jstring android_os_Parcel_readString(JNIEnv* env, jclass clazz, jlong nativePtr)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
        size_t len;
        const char16_t* str = parcel->readString16Inplace(&len);
        if (str) {
            return env->NewString(reinterpret_cast<const jchar*>(str), len);
        }
        return NULL;
    }
    return NULL;
}

static jint android_os_Parcel_readInt(JNIEnv* env, jclass clazz, jlong nativePtr)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
        return parcel->readInt32();
    }
    return 0;
}

// cpp
#define PAD_SIZE_UNSAFE(s) (((s)+3)&~3)

static size_t pad_size(size_t s) {
    if (s > (SIZE_T_MAX - 3)) {
        abort();
    }
    return PAD_SIZE_UNSAFE(s);
}

const char16_t* Parcel::readString16Inplace(size_t* outLen) const
{
    int32_t size = readInt32();
    // watch for potential int overflow from size+1
    if (size >= 0 && size < INT32_MAX) {
        *outLen = size;
        const char16_t* str = (const char16_t*)readInplace((size+1)*sizeof(char16_t));
        if (str != NULL) {
            return str;
        }
    }
    *outLen = 0;
    return NULL;
}

const void* Parcel::readInplace(size_t len) const
{
    if (len > INT32_MAX) {
        // don't accept size_t values which may have come from an
        // inadvertent conversion from a negative int.
        return NULL;
    }

    if ((mDataPos+pad_size(len)) >= mDataPos && (mDataPos+pad_size(len)) <= mDataSize
            && len <= pad_size(len)) {
        const void* data = mData+mDataPos;
        mDataPos += pad_size(len);
        ALOGV("readInplace Setting data pos of %p to %zu", this, mDataPos);
        return data;
    }
    return NULL;
}

int32_t Parcel::readInt32() const
{
    return readAligned<int32_t>();
}

template<class T>
status_t Parcel::readAligned(T *pArg) const {
    COMPILE_TIME_ASSERT_FUNCTION_SCOPE(PAD_SIZE_UNSAFE(sizeof(T)) == sizeof(T));

    if ((mDataPos+sizeof(T)) <= mDataSize) {
        const void* data = mData+mDataPos;
        mDataPos += sizeof(T);
        *pArg =  *reinterpret_cast<const T*>(data);
        return NO_ERROR;
    } else {
        return NOT_ENOUGH_DATA;
    }
}

template<class T>
T Parcel::readAligned() const {
    T result;
    if (readAligned(&result) != NO_ERROR) {
        result = 0;
    }

    return result;
}










